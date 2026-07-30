import io
import json
import logging
import zipfile
from datetime import datetime

from django.db import transaction

from notificationapp.services import send_pending_satellite_notifications
from satelliteapp.models import (
    Order,
    OrderFarm,
    OrderStatus,
    SatelliteFarmNotification,
    SatelliteResult,
)
from satelliteapp.services.alerts import sync_alerts_for_result
from satelliteapp.services.irriwatch import (
    download_result_zip,
    get_companies,
    get_orders,
    get_result_dates,
    upload_tif_to_s3,
)
from satelliteapp.services.notifications import sync_notifications_for_result

logger = logging.getLogger(__name__)


def run():
    """Walk IrriWatch companies -> orders -> result dates and ingest new results."""
    companies = get_companies()
    logger.info("Found %s companies", len(companies))

    for company in companies:
        company_uuid = company["uuid"]
        company_name = company.get("name")
        logger.info("Processing company name=%s uuid=%s", company_name, company_uuid)

        orders = get_orders(company_uuid)
        logger.info("Found %s orders for company=%s", len(orders), company_name)

        for order in orders:
            order_uuid = order["uuid"]
            order_state = (order.get("state") or "").strip().upper()

            db_order = Order.objects.filter(irriwatch_order_uuid=order_uuid).first()
            if not db_order:
                logger.warning("Order not found in DB uuid=%s, skipping", order_uuid)
                continue

            if order_state == OrderStatus.COMPLETED:
                logger.info("Skipping completed order uuid=%s", order_uuid)
                continue

            # Oldest -> newest so history-dependent rules (crop-health-dropping,
            # notification frequency windows) see prior dates already ingested.
            result_dates = sorted(
                get_result_dates(company_uuid, order_uuid),
                key=lambda result: result["date"],
            )
            logger.info(
                "Found %s result dates for order uuid=%s", len(result_dates), order_uuid
            )

            for result in result_dates:
                result_uuid = result["uuid"]
                obs_date = datetime.strptime(result["date"], "%Y%m%d").date()

                already_exists = SatelliteResult.objects.filter(
                    order_farm__order_id=db_order.id,
                    observation_date=obs_date,
                ).exists()
                if already_exists:
                    logger.info(
                        "Already ingested observation_date=%s order_uuid=%s",
                        obs_date,
                        order_uuid,
                    )
                    continue

                try:
                    _process_result_date(
                        company_uuid, order_uuid, result_uuid, obs_date
                    )
                except Exception:
                    logger.exception(
                        "Failed ingest for observation_date=%s order_uuid=%s",
                        obs_date,
                        order_uuid,
                    )
                    continue

    logger.info("Ingest run finished")


def _process_result_date(company_uuid, order_uuid, result_uuid, obs_date):
    """Download one result zip, persist results + alerts + notifications, push."""
    zip_bytes = download_result_zip(company_uuid, order_uuid, result_uuid)
    field_data, tif_urls = _extract_zip(zip_bytes, obs_date)

    created_notification_ids: list[int] = []

    with transaction.atomic():
        created_results: list[SatelliteResult] = []

        for field_uuid, field_metrics in field_data.items():
            order_farm = OrderFarm.objects.filter(
                irriwatch_field_uuid=field_uuid
            ).first()
            if not order_farm:
                logger.warning(
                    "OrderFarm not found for field_uuid=%s order_uuid=%s",
                    field_uuid,
                    order_uuid,
                )
                continue

            result_record = SatelliteResult.objects.create(
                order_farm=order_farm,
                observation_date=obs_date,
                data_json=field_metrics,
                tiff_url=tif_urls.get(field_uuid),
            )
            created_results.append(result_record)

        for result_record in created_results:
            sync_alerts_for_result(result_record)
            created = sync_notifications_for_result(result_record)
            created_notification_ids.extend(notif.id for notif in created)

    # Push AFTER commit (never send a push for a row that might roll back), and
    # only for notifications created this run whose farm is linked.
    if created_notification_ids:
        pending_qs = SatelliteFarmNotification.objects.filter(
            id__in=created_notification_ids,
            order_farm__farm__isnull=False,
        )
        if pending_qs.exists():
            sent, failed, no_devices = send_pending_satellite_notifications(pending_qs)
            logger.info(
                "Push observation_date=%s order_uuid=%s: %s sent, %s failed, %s no-device",
                obs_date,
                order_uuid,
                sent,
                failed,
                no_devices,
            )

    logger.info(
        "Saved results, alerts, notifications for observation_date=%s order_uuid=%s",
        obs_date,
        order_uuid,
    )


def _extract_zip(zip_bytes, obs_date):
    """Return (field_data dict, {field_uuid: tif_url}) from a result zip."""
    field_data = {}
    tif_urls = {}

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()

        if "field-data.json" in names:
            with zf.open("field-data.json") as f:
                field_data = json.load(f)

        for filename in names:
            if not filename.endswith(".tif"):
                continue

            field_uuid = filename[: -len(".tif")]
            tif_bytes = zf.read(filename)
            tif_urls[field_uuid] = upload_tif_to_s3(tif_bytes, field_uuid, obs_date)
            logger.info(
                "Uploaded tif field_uuid=%s observation_date=%s", field_uuid, obs_date
            )
            # TODO(png): enqueue PNG map-layer rendering for this tif (Step 3h).

    return field_data, tif_urls