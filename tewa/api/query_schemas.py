# tewa/api/query_schemas.py
from rest_framework import serializers


class RankingQuerySerializer(serializers.Serializer):
    scenario_id = serializers.IntegerField(required=True)
    da_id = serializers.IntegerField(required=False, allow_null=True)
    top_n = serializers.IntegerField(
        required=False, default=10, min_value=1, max_value=100)


class ScoreListQuerySerializer(serializers.Serializer):
    scenario_id = serializers.IntegerField(required=False)
    da_id = serializers.IntegerField(required=False)
    ordering = serializers.ChoiceField(
        required=False, default="-score",
        choices=("-score", "score", "-computed_at", "computed_at"),
    )


class ScoreBreakdownQuerySerializer(serializers.Serializer):
    scenario_id = serializers.IntegerField()
    da_id = serializers.IntegerField()
    track_id = serializers.CharField(
        required=False, allow_null=True, allow_blank=True)
