# tewa/serializers.py
from rest_framework import serializers

from tewa.models import DefendedAsset, Scenario, ThreatScore, Track, TrackSample

from .models import Scenario, Track


class DefendedAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefendedAsset
        fields = ['id', 'name', 'lat', 'lon',
                  'radius_km', 'created_at', 'updated_at']

    def validate_radius_km(self, value):
        if value <= 0:
            raise serializers.ValidationError("Radius must be positive")
        return value


# Serializer for Scenario model, explicitly specifying fields
class ScenarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scenario
        fields = ['id', 'name', 'description',
                  'start_time', 'end_time', 'notes']

# Serializer for Track model, explicitly specifying fields


class TrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Track
        fields = [
            'track_id', 'scenario', 'lat', 'lon', 'alt_m',
            'speed_mps', 'heading_deg', 'created_at', 'updated_at'
        ]

# Serializer for TrackSample model, explicitly specifying fields


class TrackSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackSample
        fields = ['id', 'track', 't', 'lat', 'lon',
                  'alt_m', 'speed_mps', 'heading_deg']

# Serializer for ThreatScore model, including related fields for DA and Track


class ThreatScoreSerializer(serializers.ModelSerializer):
    da_name = serializers.CharField(source="da.name", read_only=True)
    track_id = serializers.CharField(source="track.track_id", read_only=True)

    class Meta:
        model = ThreatScore
        fields = [
            "id", "scenario", "track", "da", "track_id", "da_name",
            "cpa_km", "tcpa_s", "tdb_km", "twrp_s", "score", "computed_at"
        ]


# tewa/serializers.py
