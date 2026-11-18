import logging
from django.conf import settings
from farmerapp.models import FarmSatelliteSubscription
from satelliteapp.models import (
    Company,
    Order,
    OrderFarm,
    OrderFarmStatus,
    OrderStatus,
)
from satelliteapp.services.irriwatch import get_companies, get_orders

logger = logging.getLogger(__name__)


def _map_order_status(irriwatch_state):
    state = (irriwatch_state or "").strip().upper()
    if state == OrderStatus.COMPLETED:
        return OrderStatus.COMPLETED
    return OrderStatus.ACTIVE


def _map_order_farm_status(order_status):
    if order_status == OrderStatus.COMPLETED:
        return OrderFarmStatus.COMPLETED
    return OrderFarmStatus.SYNCING


def run():
    """Walk IrriWatch companies -> orders -> fields and upsert Company/Order/OrderFarm."""
    companies = get_companies()
    logger.info("Found %s companies", len(companies))

    for company in companies:
        db_company, _ = Company.objects.get_or_create(
            company_uuid=company["uuid"],
            defaults={"company_name": company["name"]},
        )

        orders = get_orders(company["uuid"])
        logger.info("Found %s orders for company=%s", len(orders), company["name"])

        for order in orders:
            order_status = _map_order_status(order.get("state"))

            features = order.get("fields", {}).get("features", [])
            field_uuids = [
                f.get("properties", {}).get("uuid")
                for f in features
                if f.get("properties", {}).get("uuid")
            ]

            subs_by_uuid = {
                sub.irriwatch_field_uuid: sub
                for sub in FarmSatelliteSubscription.objects.filter(
                    irriwatch_field_uuid__in=field_uuids
                ).select_related("farm")
            }

            if settings.SATELLITE_SYNC_LOCAL_FARMS_ONLY:
                field_uuids = [u for u in field_uuids if u in subs_by_uuid]
                if not field_uuids:
                    logger.info(
                        "Local-only sync: no local farms in order uuid=%s, skipping",
                        order["uuid"],
                    )
                    continue

            db_order, _ = Order.objects.update_or_create(
                irriwatch_order_uuid=order["uuid"],
                defaults={"company": db_company, "status": order_status},
            )

            for field_uuid in field_uuids:
                sub = subs_by_uuid.get(field_uuid)
                OrderFarm.objects.update_or_create(
                    irriwatch_field_uuid=field_uuid,
                    defaults={
                        "order": db_order,
                        "farm": sub.farm if sub else None,
                        "status": _map_order_farm_status(order_status),
                    },
                )
