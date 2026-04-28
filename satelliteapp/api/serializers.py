from rest_framework import serializers

class SatelliteBatchEventSerializer(serializers.Serializer):
    event_id = serializers.IntegerField()
    event_type = serializers.CharField()
    generated_at = serializers.DateTimeField()
    external_id = serializers.IntegerField(required=False, allow_null=True)
    order_field_id = serializers.IntegerField()
    observation_date = serializers.DateField()
    alerts = serializers.ListField(child=serializers.JSONField(), required=False)
    notifications = serializers.ListField(child=serializers.JSONField(), required=False)

class SatelliteBatchPayloadSerializer(serializers.Serializer):
    batch_id = serializers.CharField()
    generated_at = serializers.DateTimeField()
    events = SatelliteBatchEventSerializer(many=True)
