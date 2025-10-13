# tewa/api/serializers.py

from rest_framework import serializers

from tewa.models import DefendedAsset, Scenario, ThreatScore, Track, TrackSample

# -----------------------------
# Existing serializers
# -----------------------------


class TrackSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackSample
        fields = ['id', 'track', 't', 'lat', 'lon',
                  'alt_m', 'speed_mps', 'heading_deg']


class ThreatScoreSerializer(serializers.ModelSerializer):
    da_name = serializers.CharField(source="da.name", read_only=True)
    track_id = serializers.CharField(source="track.track_id", read_only=True)

    class Meta:
        model = ThreatScore
        fields = [
            "id", "scenario", "track", "da", "track_id", "da_name",
            "cpa_km", "tcpa_s", "tdb_km", "twrp_s", "score", "computed_at"
        ]

# -----------------------------
# New serializer for compute POST
# -----------------------------


class ComputeThreatSerializer(serializers.Serializer):
    scenario_id = serializers.IntegerField()
    da_id = serializers.PrimaryKeyRelatedField(
        queryset=DefendedAsset.objects.all(), source="da"
    )
    track_id = serializers.PrimaryKeyRelatedField(
        queryset=Track.objects.all(), source="track"
    )

    def validate(self, attrs):
        track = attrs['track']
        scenario_id = attrs.get('scenario_id')  # safer than initial_data
        if track.scenario.id != scenario_id:
            raise serializers.ValidationError(
                "Track does not belong to the given scenario.")
        return attrs

# tewa/api/serializers.py


class DefendedAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefendedAsset
        fields = ['id', 'name', 'lat', 'lon',
                  'radius_km', 'created_at', 'updated_at']


class ScenarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scenario
        fields = ['id', 'name', 'start_time', 'end_time', 'notes']


# tewa/serializers.py


class TrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Track
        fields = ['id', 'track_id', 'lat', 'lon', 'alt_m',
                  'speed_mps', 'heading_deg', 'scenario']


class ScoreBreakdownQuerySerializer(serializers.Serializer):
    scenario_id = serializers.IntegerField()
    da_id = serializers.IntegerField()       # <— changed
    track_id = serializers.IntegerField()
