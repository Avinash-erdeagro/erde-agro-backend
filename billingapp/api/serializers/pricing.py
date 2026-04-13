from rest_framework import serializers


class SatellitePricingRequestSerializer(serializers.Serializer):
    farm_id = serializers.IntegerField(required=False, min_value=1)
    farm_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=False,
    )

    def validate(self, attrs):
        farm_id = attrs.get("farm_id")
        farm_ids = attrs.get("farm_ids")

        if farm_id and farm_ids:
            raise serializers.ValidationError(
                "Provide either farm_id or farm_ids, not both."
            )

        if not farm_id and not farm_ids:
            raise serializers.ValidationError(
                "Either farm_id or farm_ids is required."
            )

        normalized_farm_ids = farm_ids or [farm_id]
        attrs["farm_ids"] = list(dict.fromkeys(normalized_farm_ids))
        return attrs
