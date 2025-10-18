# core/api/serializers.py

from core.models import FlightInfo
from rest_framework import serializers

from core.models import CrewDetail, SiteConfig, TWCCConfiguration


class ConfigurationSerializer(serializers.Serializer):
    """Pass-through JSON payload (for config endpoints that just store a blob)."""
    payload = serializers.JSONField()


class CrewDetailSerializer(serializers.ModelSerializer):
    """Canonical serializer for CrewDetail using current field names."""
    class Meta:
        model = CrewDetail
        fields = [
            "id",
            "unit_no",
            "flight_no",
            "crew_role",
            "crew_name",
            "personal_no",
            "cat_state",
            "current_datetime",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CrewDetailIngestSerializer(serializers.ModelSerializer):
    """
    Back-compat ingest serializer that maps legacy keys to canonical fields.
    Accepts:
      unitno      -> unit_no
      flightno    -> flight_no
      crewrole    -> crew_role
      crewname    -> crew_name
      personalno  -> personal_no
      catstate    -> cat_state
      datetime    -> current_datetime
    """
    unitno = serializers.CharField(write_only=True, required=False)
    flightno = serializers.CharField(write_only=True, required=False)
    crewrole = serializers.CharField(write_only=True, required=False)
    crewname = serializers.CharField(write_only=True, required=False)
    personalno = serializers.CharField(write_only=True, required=False)
    catstate = serializers.CharField(write_only=True, required=False)
    datetime = serializers.DateTimeField(write_only=True, required=False)

    class Meta:
        model = CrewDetail
        fields = [
            # canonical fields
            "id",
            "unit_no",
            "flight_no",
            "crew_role",
            "crew_name",
            "personal_no",
            "cat_state",
            "current_datetime",
            "created_at",
            # legacy write-only aliases
            "unitno",
            "flightno",
            "crewrole",
            "crewname",
            "personalno",
            "catstate",
            "datetime",
        ]
        read_only_fields = ["id", "created_at"]
        # allow legacy aliases to supply values
        extra_kwargs = {
            "unit_no": {"required": False},
            "flight_no": {"required": False},
            "crew_role": {"required": False},
            "crew_name": {"required": False},
            "personal_no": {"required": False},
            "cat_state": {"required": False},
            "current_datetime": {"required": False},
        }

    def validate(self, attrs):
        mapping = {
            "unitno": "unit_no",
            "flightno": "flight_no",
            "crewrole": "crew_role",
            "crewname": "crew_name",
            "personalno": "personal_no",
            "catstate": "cat_state",
            "datetime": "current_datetime",
        }
        for legacy, canonical in mapping.items():
            if legacy in attrs and attrs[legacy] is not None:
                attrs[canonical] = attrs.pop(legacy)
        return attrs


class TWCCConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TWCCConfiguration
        fields = "__all__"


class SiteConfigSerializer(serializers.ModelSerializer):
    # Keep only fields that actually exist on the model
    class Meta:
        model = SiteConfig
        fields = ["key", "payload"]


class FlightInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlightInfo
        fields = "__all__"
