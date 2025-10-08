# tewa/models.py

from __future__ import annotations

import math

# assuming TimeStamped has created_at, updated_at
from django.core.exceptions import ValidationError

# ---------- Base ----------
from django.db import models
from django.utils import timezone


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DefendedAsset(models.Model):
    id = models.BigAutoField(primary_key=True)  # Ensure it's included

    name = models.CharField(max_length=255)
    lat = models.FloatField()
    lon = models.FloatField()
    radius_km = models.FloatField()
    created_at = models.DateTimeField(
        auto_now_add=True)  # Set on object creation
    # Automatically updates on save
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Ensure the radius is between 0 and 1000 km
        if self.radius_km <= 0 or self.radius_km > 1000:
            raise ValidationError('Radius must be between 0 and 1000 km.')

    def __str__(self):
        return f"{self.name} at {self.lat}, {self.lon} with radius {self.radius_km} km"


class Scenario(models.Model):
    """
    Represents a TEWA scenario, containing DAs, Tracks, and config.
    """
    id = models.BigAutoField(primary_key=True)  # Ensure it's included

    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, null=True)

    # Added to match existing fixture
    # Make sure this is DateTimeField
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Track(TimeStamped):
    """
    A logical target/aircraft identity.
    'track_id' is external/system ID (radar/fusion ID); not necessarily unique globally,
    but we keep it unique per Scenario when scenario is set.
    """
    scenario = models.ForeignKey(
        Scenario, on_delete=models.CASCADE, related_name="tracks",
        null=True, blank=True,  # keep optional to avoid breaking existing code
    )
    track_id = models.CharField(max_length=64)
    # Most recent kinematic snapshot (redundant convenience fields)
    lat = models.FloatField()
    lon = models.FloatField()
    alt_m = models.FloatField()
    speed_mps = models.FloatField()
    heading_deg = models.FloatField()

    def __str__(self) -> str:
        return f"{self.track_id}" + (f" @ {self.scenario.name}" if self.scenario else "")

    class Meta:
        unique_together = [("scenario", "track_id")]
        indexes = [
            models.Index(fields=["scenario", "track_id"]),
            models.Index(fields=["lat", "lon"]),
        ]


class TrackSample(TimeStamped):
    """
    Time-series positions per Track (raw or fused).
    """
    track = models.ForeignKey(
        Track, on_delete=models.CASCADE, related_name="samples"
    )
    t = models.DateTimeField()  # sample timestamp
    lat = models.FloatField()
    lon = models.FloatField()
    alt_m = models.FloatField()
    speed_mps = models.FloatField()
    heading_deg = models.FloatField()

    def __str__(self) -> str:
        return f"{self.track.track_id} @ {self.t.isoformat()}"

    class Meta:
        ordering = ["t"]
        indexes = [
            models.Index(fields=["track", "t"]),
            models.Index(fields=["lat", "lon"]),
        ]
        unique_together = [("track", "t")]


class ThreatScore(TimeStamped):
    """
    Output of the deterministic threat evaluation for a (Track, DA) at a given instant.
    """
    scenario = models.ForeignKey(
        Scenario, on_delete=models.CASCADE, related_name="threat_scores",
        null=True, blank=True,  # optional for now to keep existing code working
    )
    track = models.ForeignKey(
        Track, on_delete=models.CASCADE, related_name="threat_scores"
    )
    da = models.ForeignKey(
        DefendedAsset, on_delete=models.CASCADE, related_name="threat_scores"
    )

    # Raw model components (optional; nullable if not computed)
    cpa_km = models.FloatField(null=True, blank=True)
    tcpa_s = models.FloatField(null=True, blank=True)
    tdb_km = models.FloatField(null=True, blank=True)
    twrp_s = models.FloatField(null=True, blank=True)

    # Final normalized/weighted score (0..1 typically)
    score = models.FloatField(null=True, blank=True)

    computed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        left = self.scenario.name if self.scenario else "NoScenario"
        return f"ThreatScore[{left} | {self.track.track_id} → {self.da.name}]"

    class Meta:
        indexes = [
            models.Index(fields=["scenario", "da", "computed_at"]),
            models.Index(fields=["scenario", "track", "computed_at"]),
        ]
        unique_together = [("scenario", "track", "da", "computed_at")]

# tewa/models.py


class ModelParams(models.Model):
    """
    Parameter set (weights, normalizers) used by deterministic threat models.
    Scope: per Scenario (default one-to-one).
    """
    scenario = models.OneToOneField(
        'Scenario', on_delete=models.CASCADE, related_name='params'
    )

    # Weights for various factors in the threat model (CPA, TCPA, TDB, TWRP)
    w_cpa = models.FloatField(default=0.25)
    w_tcpa = models.FloatField(default=0.25)
    w_tdb = models.FloatField(default=0.25)
    w_twrp = models.FloatField(default=0.25)

    # Normalization scales for CPA, TCPA, TDB, TWRP
    cpa_scale_km = models.FloatField(default=20.0)
    tcpa_scale_s = models.FloatField(default=120.0)
    tdb_scale_km = models.FloatField(default=30.0)
    twrp_scale_s = models.FloatField(default=120.0)

    # Optional flag to clamp values between 0 and 1
    clamp_0_1 = models.BooleanField(default=True)

    # Timestamps for creation and updates
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Params for {self.scenario.name}"
