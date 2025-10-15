# tewa/serializers.py
from rest_framework import serializers

from tewa.models import Track


class TrackSlimSerializer(serializers.ModelSerializer):
    class Meta:
        model = Track
        fields = ["track_id", "lat", "lon"]
