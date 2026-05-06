from django.db import IntegrityError, transaction
from rest_framework import status

from authapp.api.responses import api_response
from authapp.api.views.base import BaseAPIView
from satelliteapp.api.serializers import SatelliteBatchPayloadSerializer
from satelliteapp.models import SatelliteEventReceipt
from satelliteapp.services.signature import verify_satellite_signature
from satelliteapp.tasks import process_satellite_receipt


class SatelliteBatchReceiverView(BaseAPIView):
    authentication_classes = []
    permission_classes = []

    signature_header_name = "X-Satellite-Event-Signature"

    @staticmethod
    def _append_once(items, value):
        if value not in items:
            items.append(value)

    def post(self, request):
        signature = request.headers.get(self.signature_header_name, "")
        raw_body = request.body

        if not signature:
            return api_response(
                success=False,
                message="Missing satellite event signature.",
                result=None,
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if not verify_satellite_signature(raw_body, signature):
            return api_response(
                success=False,
                message="Invalid satellite event signature.",
                result=None,
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = SatelliteBatchPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        batch_id = serializer.validated_data["batch_id"]
        events = serializer.validated_data["events"]
        raw_events = request.data.get("events", [])

        incoming_event_ids = [event["event_id"] for event in events]
        existing_event_ids = set(
            SatelliteEventReceipt.objects.filter(event_id__in=incoming_event_ids)
            .values_list("event_id", flat=True)
        )

        accepted_event_ids = []
        duplicate_event_ids = []
        failed_event_ids = []
        seen_in_batch = set()
        receipt_objects = []
        fallback_events = []

        for event, raw_event in zip(events, raw_events):
            event_id = event["event_id"]

            if event_id in existing_event_ids or event_id in seen_in_batch:
                duplicate_event_ids.append(event_id)
                continue

            seen_in_batch.add(event_id)

            receipt_objects.append(
                SatelliteEventReceipt(
                    event_id=event_id,
                    batch_id=batch_id,
                    event_type=event["event_type"],
                    external_id=event.get("external_id"),
                    order_field_id=event["order_field_id"],
                    observation_date=event["observation_date"],
                    generated_at=event["generated_at"],
                    payload_json=raw_event,
                )
            )
            fallback_events.append((event_id, event, raw_event))
            accepted_event_ids.append(event_id)

        if receipt_objects:
            try:
                with transaction.atomic():
                    created_receipts = SatelliteEventReceipt.objects.bulk_create(receipt_objects)
            except IntegrityError:
                accepted_event_ids = []
                created_receipts = []

                for event_id, event, raw_event in fallback_events:
                    try:
                        receipt, created = SatelliteEventReceipt.objects.get_or_create(
                            event_id=event_id,
                            defaults={
                                "batch_id": batch_id,
                                "event_type": event["event_type"],
                                "external_id": event.get("external_id"),
                                "order_field_id": event["order_field_id"],
                                "observation_date": event["observation_date"],
                                "generated_at": event["generated_at"],
                                "payload_json": raw_event,
                            },
                        )
                    except Exception:
                        self._append_once(failed_event_ids, event_id)
                        continue

                    if created:
                        self._append_once(accepted_event_ids, event_id)
                        created_receipts.append(receipt)
                    else:
                        self._append_once(duplicate_event_ids, event_id)

            for receipt in created_receipts:
                process_satellite_receipt.delay(receipt.id)

        return api_response(
            success=True,
            message="Satellite event batch received successfully.",
            result={
                "accepted_event_ids": accepted_event_ids,
                "duplicate_event_ids": duplicate_event_ids,
                "failed_event_ids": failed_event_ids,
            },
            status_code=status.HTTP_200_OK,
        )
