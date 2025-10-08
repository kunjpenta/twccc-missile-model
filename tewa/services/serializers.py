# tewa/serializers.py
from rest_framework import serializers

from tewa.models import DefendedAsset, ThreatScore


class DefendedAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefendedAsset
        fields = "__all__"


class TrackInputSerializer(serializers.Serializer):
    track_id = serializers.CharField(max_length=64)
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    alt_m = serializers.FloatField()
    speed_mps = serializers.FloatField()
    heading_deg = serializers.FloatField()


class ThreatComputeSerializer(serializers.Serializer):
    da_id = serializers.IntegerField()
    weapon_range_km = serializers.FloatField(required=False, allow_null=True)

    # Inline nested track input
    track = TrackInputSerializer()


class ThreatScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThreatScore
        fields = ["id", "track", "da", "cpa_km", "tcpa_s",
                  "tdb_km", "twrp_s", "score", "computed_at"]
        depth = 1
