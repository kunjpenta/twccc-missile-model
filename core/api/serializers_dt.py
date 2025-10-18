# core/api/serializers_dt.py
from __future__ import annotations

from rest_framework import serializers

from core.enums import EngagementActionEnum, OrderStatusEnum


class EngagementOrderDTOSerializer(serializers.Serializer):
    track_no = serializers.CharField(max_length=50, required=True)
    unit_id = serializers.IntegerField(required=True)
    flight = serializers.CharField(
        max_length=50, required=False, allow_blank=True)
    order_status = serializers.ChoiceField(
        choices=[(tag.value, tag.name) for tag in OrderStatusEnum],
        required=False,
        allow_null=True,
    )
    ack_status = serializers.ChoiceField(
        choices=[(tag.value, tag.name) for tag in OrderStatusEnum],
        required=False,
        allow_null=True,
    )
    engagement_type = serializers.ChoiceField(
        choices=[(tag.value, tag.name) for tag in EngagementActionEnum],
        required=True,
    )
    source_user_mode = serializers.IntegerField(
        required=False, allow_null=True)


class AssignTrackDTOSerializer(serializers.Serializer):
    track_no = serializers.CharField()
    unit = serializers.IntegerField()
    flight = serializers.CharField()
    launch_type = serializers.IntegerField(required=False, allow_null=True)
    launch_time = serializers.DateTimeField(required=False, allow_null=True)
    key = serializers.CharField(required=False, allow_blank=True)
