from rest_framework import serializers


class FarmerSatelliteOverviewQuerySerializer(serializers.Serializer):
    observation_date = serializers.DateField()
