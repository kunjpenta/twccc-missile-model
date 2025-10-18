from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


# ---------------------------
# Auth
# ---------------------------
class User(AbstractUser):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("operator", "Operator"),
        ("viewer", "Viewer"),
    ]
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default="viewer")

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self) -> str:
        return self.username


# ---------------------------
# Crew / Roles
# ---------------------------
class CrewRole(models.Model):
    """Lookup table for standardized crew roles (e.g., Pilot, WSO, ATC)."""
    role_id = models.IntegerField(unique=True)
    role_name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["role_name"]

    def __str__(self) -> str:
        return self.role_name


class CrewDetailsLegacy(models.Model):
    """
    Legacy shape kept for ingestion/back-compat:
      unitno -> unit_no
      flightno -> flight_no
      crewrole -> crew_role
      crewname -> crew_name
      personalno -> personal_no
      catstate -> cat_state
      datetime -> current_datetime
    Prefer writing to CrewDetail; keep this for staging/imports.
    """
    id = models.BigAutoField(primary_key=True)
    unitno = models.IntegerField()
    flightno = models.CharField(max_length=100)
    crewrole = models.CharField(max_length=100)
    crewname = models.CharField(max_length=100)
    personalno = models.CharField(max_length=100)
    catstate = models.CharField(max_length=100)
    datetime = models.DateTimeField()

    class Meta:
        db_table = "core_crewdetails_legacy"
        ordering = ["-datetime", "-id"]
        indexes = [
            models.Index(fields=["unitno", "flightno"]),
            models.Index(fields=["personalno"]),
            models.Index(fields=["datetime"]),
        ]

    def __str__(self) -> str:
        return f"{self.crewname} - {self.flightno}"


class CrewDetail(models.Model):
    """Canonical crew detail row used by the API and serializers."""
    id = models.BigAutoField(primary_key=True)

    unit_no = models.CharField(max_length=32, db_index=True)
    flight_no = models.CharField(max_length=32, db_index=True)
    # Consider FK to CrewRole later if you want strict roles:
    crew_role = models.CharField(max_length=64)
    crew_name = models.CharField(max_length=128)
    personal_no = models.CharField(max_length=64, db_index=True)
    # e.g., Active / Reserve / CAT-I
    cat_state = models.CharField(max_length=64)
    # source timestamp (not auto_now)
    current_datetime = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-current_datetime", "-id"]
        verbose_name = "Crew Detail"
        verbose_name_plural = "Crew Details"
        indexes = [
            models.Index(fields=["unit_no", "flight_no"]),
            models.Index(fields=["personal_no"]),
            models.Index(fields=["current_datetime"]),
        ]
        # unique_together = ("unit_no", "flight_no", "crew_name", "current_datetime")

    def __str__(self) -> str:
        return f"{self.unit_no}/{self.flight_no} | {self.crew_name} ({self.crew_role})"


# ---------------------------
# Configuration / Settings
# ---------------------------
class TWCCConfiguration(models.Model):
    """
    System configuration stored as a single active row.
    - Explicit network settings (IP/ports)
    - payload/version/is_active + timestamps used by the service
    """
    # Service-friendly fields
    payload = models.JSONField(default=dict, blank=True)
    version = models.CharField(max_length=32, default="v1")
    is_active = models.BooleanField(default=True)

    # Network settings
    ows_ip = models.CharField(max_length=255, default="127.0.0.1")
    wa_ip = models.CharField(max_length=255, default="127.0.0.1")
    if_ip = models.CharField(max_length=255, default="127.0.0.1")
    db_ip = models.CharField(max_length=255, default="127.0.0.1")

    ows_track_port = models.IntegerField(default=54674)
    ows_nrt_port = models.IntegerField(default=6005)
    ows_internal_comm_port = models.IntegerField(default=6006)
    wa_port = models.IntegerField(default=6002)
    if_port = models.IntegerField(default=6007)

    recording_flag = models.BooleanField(default=False)
    record_interval = models.IntegerField(default=1)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "TWCC Configuration"
        verbose_name_plural = "TWCC Configurations"

    def __str__(self) -> str:
        return f"TWCCConfiguration(id={self.pk}, version={self.version}, active={self.is_active})"


class SiteConfig(models.Model):
    key = models.CharField(max_length=64, unique=True)
    payload = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key


class FlightInfo(models.Model):
    """
    Basic mapping of unit->flight and its SAGW weapon type.
    """
    unitno = models.IntegerField(db_index=True)
    flightno = models.CharField(max_length=255, db_index=True)
    type_of_sagw_weapon = models.IntegerField()

    class Meta:
        ordering = ["unitno", "flightno"]
        indexes = [
            models.Index(fields=["unitno", "flightno"]),
        ]
        # If each (unitno, flightno) must be unique, uncomment:
        # unique_together = ("unitno", "flightno")

    def __str__(self) -> str:
        return f"{self.unitno}_{self.flightno}"
