# tewa/api/serializers.py
from __future__ import annotations
from typing import cast

from rest_framework import serializers

from tewa.models import ModelParams

from ..models import (
    DefendedAsset,
    Scenario,
    ThreatScore,
    Track,
    TrackSample,
)

# ---------- Model serializers used by views_read.py ----------


class ScenarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scenario
        fields = "__all__"


class DefendedAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefendedAsset
        fields = "__all__"


class TrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Track
        fields = "__all__"


class TrackSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackSample
        fields = "__all__"


class ThreatScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThreatScore
        fields = "__all__"


# ---------- Task 21: Score breakdown serializer ----------

class MetricsSerializer(serializers.Serializer):
    cpa_m = serializers.FloatField()
    tcpa_s = serializers.FloatField()
    tdb_s = serializers.FloatField()
    twrp_s = serializers.FloatField()


class NormalizedSerializer(serializers.Serializer):
    cpa = serializers.FloatField()
    tcpa = serializers.FloatField()
    tdb = serializers.FloatField()
    twrp = serializers.FloatField()


class WeightsSerializer(serializers.Serializer):
    cpa = serializers.FloatField()
    tcpa = serializers.FloatField()
    tdb = serializers.FloatField()
    twrp = serializers.FloatField()


class ContributionsSerializer(serializers.Serializer):
    cpa = serializers.FloatField()
    tcpa = serializers.FloatField()
    tdb = serializers.FloatField()
    twrp = serializers.FloatField()


class ParamsSerializer(serializers.Serializer):
    # empty on purpose for now
    pass


class ScoreBreakdownSerializer(serializers.Serializer):
    scenario_id = serializers.IntegerField()
    track_id = serializers.CharField()
    da_id = serializers.IntegerField()
    computed_at = serializers.DateTimeField()
    metrics = MetricsSerializer()
    normalized = NormalizedSerializer()
    weights = WeightsSerializer()
    contributions = ContributionsSerializer()
    score = serializers.FloatField()
    params = ParamsSerializer()
    explain = serializers.ListField(child=serializers.CharField())

    # legacy passthroughs for backward-compat tests/UI
    cpa_km = serializers.FloatField(required=False, allow_null=True)
    tcpa_s = serializers.FloatField(required=False, allow_null=True)
    tdb_km = serializers.FloatField(required=False, allow_null=True)
    twrp_s = serializers.FloatField(required=False, allow_null=True)
    total_score = serializers.FloatField(required=False, allow_null=True)

# tewa/api/serializers.py


class ScenarioParamsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelParams
        fields = [
            "scenario",
            "R_W_m", "R_DA_m", "tick_s",
            "w_cpa", "w_tcpa", "w_tdb", "w_twrp",
            "sigma_cpa", "sigma_tcpa", "sigma_tdb", "sigma_twrp",
            "updated_at",
        ]
        read_only_fields = ["scenario", "updated_at"]

    def validate(self, attrs):
        # Merge instance values with incoming attrs for cross-field validation
        data = {**{f: getattr(self.instance, f, None)
                   for f in self.fields}, **attrs}

        def _f(x):
            return float(x) if x is not None else 0.0

        wsum = _f(data.get("w_cpa")) + _f(data.get("w_tcpa")) + \
            _f(data.get("w_tdb")) + _f(data.get("w_twrp"))
        if abs(wsum - 1.0) > 1e-6:
            raise serializers.ValidationError("Weights must sum to 1.0")

        tick = data.get("tick_s")
        if tick is None or tick <= 0:
            raise serializers.ValidationError("tick_s must be > 0")

        R_W, R_DA = data.get("R_W_m"), data.get("R_DA_m")
        if R_W is not None and R_DA is not None and R_DA >= R_W:
            raise serializers.ValidationError("R_DA_m must be < R_W_m")

        return attrs
