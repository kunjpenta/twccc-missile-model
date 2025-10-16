# tewa/models.py

from __future__ import annotations

import uuid
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.dateparse import parse_datetime


# ---------- Base ----------
class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------- Validators ----------
lat_validator = [MinValueValidator(-90.0), MaxValueValidator(90.0)]
lon_validator = [MinValueValidator(-180.0), MaxValueValidator(180.0)]
heading_validator = [MinValueValidator(0.0), MaxValueValidator(360.0)]
nonneg_validator = [MinValueValidator(0.0)]  # for speed, alt if you prefer >=0


# tewa/models.py


# Reuse these if you already defined them globally
lat_validator = [MinValueValidator(-90.0),  MaxValueValidator(90.0)]
lon_validator = [MinValueValidator(-180.0), MaxValueValidator(180.0)]


# assume these validators already exist in your module
# from .validators import lat_validator, lon_validator


class Scenario(models.Model):
    id = models.BigAutoField(primary_key=True)

    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, null=True)

    start_time = models.DateTimeField(blank=True, null=True, db_index=True)
    end_time = models.DateTimeField(blank=True, null=True, db_index=True)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class DefendedAsset(models.Model):
    id = models.BigAutoField(primary_key=True)

    # Make scenario optional so tests can create DA without one
    scenario = models.ForeignKey(
        "Scenario",
        on_delete=models.CASCADE,
        related_name="defended_assets",
        null=True,
        blank=True,
        db_index=True,
    )

    name = models.CharField(max_length=255, db_index=True)
    lat = models.FloatField(validators=lat_validator)
    lon = models.FloatField(validators=lon_validator)
    radius_km = models.FloatField(
        validators=[MinValueValidator(0.001), MaxValueValidator(1000.0)]
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.radius_km is not None:
            try:
                val = float(self.radius_km)
            except (TypeError, ValueError):
                raise ValidationError("Radius_km must be a number.")
            if not (0 < val <= 1000):
                raise ValidationError(
                    "Radius_km must be between 0 and 1000 km.")

    def __str__(self) -> str:
        # radius without trailing .0; lat/lon printed as given
        r = float(self.radius_km)
        r_str = str(int(r)) if r.is_integer() else str(r)
        return f"{self.name} at {self.lat}, {self.lon} with radius {r_str} km"

    class Meta:
        indexes = [
            models.Index(fields=["scenario", "name"], name="idx_da_scn_name"),
            models.Index(fields=["lat", "lon"], name="idx_da_lat_lon"),
        ]
        unique_together = [("scenario", "name")]


class Track(TimeStamped):
    scenario = models.ForeignKey(
        Scenario, on_delete=models.CASCADE, related_name="tracks",
        null=False, blank=False, db_index=True
    )
    track_id = models.CharField(max_length=64, db_index=True)

    lat = models.FloatField(validators=lat_validator)
    lon = models.FloatField(validators=lon_validator)
    alt_m = models.FloatField()  # add nonneg validator if you require >= 0
    speed_mps = models.FloatField(validators=nonneg_validator)
    heading_deg = models.FloatField(validators=heading_validator)

    def __str__(self) -> str:
        return f"{self.track_id} @ {self.scenario.name}"

    class Meta:
        unique_together = [("scenario", "track_id")]
        indexes = [
            models.Index(fields=["scenario", "track_id"],
                         name="idx_track_scn_id"),
            models.Index(fields=["lat", "lon"], name="idx_track_lat_lon"),
            models.Index(fields=["scenario"], name="idx_track_scn"),
        ]


# ---------- TrackSample ----------
class TrackSample(TimeStamped):
    track = models.ForeignKey(
        Track, on_delete=models.CASCADE, related_name="samples", db_index=True
    )
    t = models.DateTimeField(db_index=True)  # sample timestamp
    lat = models.FloatField(validators=lat_validator)
    lon = models.FloatField(validators=lon_validator)
    alt_m = models.FloatField()
    speed_mps = models.FloatField(validators=nonneg_validator)
    heading_deg = models.FloatField(validators=heading_validator)

    def __str__(self) -> str:
        return f"{self.track.track_id} @ {self.t.isoformat()}"

    class Meta:
        ordering = ["t"]
        unique_together = [("track", "t")]
        indexes = [
            models.Index(fields=["track", "t"], name="idx_sample_track_t"),
            models.Index(fields=["lat", "lon"], name="idx_sample_lat_lon"),
        ]


# ---------- ThreatScore ----------
class ThreatScore(TimeStamped):
    """
    Output of the deterministic threat evaluation for a (Track, DA) at a given instant.
    """
    scenario = models.ForeignKey(
        Scenario, on_delete=models.CASCADE, related_name="threat_scores",
        null=False, blank=False, db_index=True
    )
    track = models.ForeignKey(
        Track, on_delete=models.CASCADE, related_name="threat_scores", db_index=True
    )
    da = models.ForeignKey(
        DefendedAsset, on_delete=models.CASCADE, related_name="threat_scores", db_index=True
    )

    # Optional batch tag to group rows produced by a single compute call
    batch_id = models.UUIDField(
        default=uuid.uuid4,  # <-- now uuid is used
        editable=False,
        db_index=True,
        null=False,  # if you want it mandatory
        blank=False,  # if you want it optional
    )

    # Raw components (nullable if not computed)
    cpa_km = models.FloatField(null=True, blank=True)
    tcpa_s = models.FloatField(null=True, blank=True)
    tdb_km = models.FloatField(null=True, blank=True)
    twrp_s = models.FloatField(null=True, blank=True)

    # Final score
    score = models.FloatField(null=True, blank=True)

    # When the compute considered the state
    computed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self) -> str:
        return f"ThreatScore[{self.scenario.name} | {self.track.track_id} → {self.da.name}]"

    class Meta:
        indexes = [
            models.Index(fields=["scenario", "da",
                         "-computed_at"], name="idx_ts_scn_da_cmp"),
            models.Index(fields=["scenario", "track",
                         "-computed_at"], name="idx_ts_scn_trk_cmp"),
            models.Index(fields=["batch_id"], name="idx_ts_batch"),
        ]
        # No unique_together on computed_at to avoid collisions

# ---------- ModelParams ----------


class ModelParams(models.Model):
    """
    Parameter set (weights, normalizers) used by deterministic threat models.
    Scope: per Scenario (default one-to-one).
    """
    scenario = models.OneToOneField(
        Scenario, on_delete=models.CASCADE, related_name='params'
    )

    w_cpa = models.FloatField(default=0.25)
    w_tcpa = models.FloatField(default=0.25)
    w_tdb = models.FloatField(default=0.25)
    w_twrp = models.FloatField(default=0.25)

    cpa_scale_km = models.FloatField(default=20.0)
    tcpa_scale_s = models.FloatField(default=120.0)
    tdb_scale_km = models.FloatField(default=30.0)
    twrp_scale_s = models.FloatField(default=120.0)

    clamp_0_1 = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    R_W_m = models.PositiveIntegerField(
        default=25000, help_text="Weapon range (m)")
    R_DA_m = models.PositiveIntegerField(
        default=8000, help_text="DA radius (m)")
    tick_s = models.FloatField(default=1.0, validators=[
                               MinValueValidator(1e-6)], help_text="Tick rate (s)")

    # Weights (UI enforces sum=1)
    w_cpa = models.FloatField(default=0.35, validators=[
                              MinValueValidator(0.0), MaxValueValidator(1.0)])
    w_tcpa = models.FloatField(default=0.25, validators=[
                               MinValueValidator(0.0), MaxValueValidator(1.0)])
    w_tdb = models.FloatField(default=0.20, validators=[
                              MinValueValidator(0.0), MaxValueValidator(1.0)])
    w_twrp = models.FloatField(default=0.20, validators=[
                               MinValueValidator(0.0), MaxValueValidator(1.0)])

    # Optional sigmas
    sigma_cpa = models.FloatField(null=True, blank=True)
    sigma_tcpa = models.FloatField(null=True, blank=True)
    sigma_tdb = models.FloatField(null=True, blank=True)
    sigma_twrp = models.FloatField(null=True, blank=True)

    # Optional audit
    updated_by = models.ForeignKey(
        getattr(settings, "AUTH_USER_MODEL", "auth.User"),
        null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_params"
    )

    def __str__(self):
        return f"Params for {self.scenario.name}"


# tewa/models.py (snippets)
# tewa/models.py

# imports at top of file


class ThreatScoreQuerySet(models.QuerySet):
    def for_key(self, *, scenario_id: int, da_id: int, track_id: int) -> "ThreatScoreQuerySet":
        return self.filter(scenario_id=scenario_id, da_id=da_id, track_id=track_id)

    def at_or_latest(self, at_iso: Optional[str] = None):
        qs = self
        if at_iso:
            at_dt = parse_datetime(at_iso)
            if at_dt:
                qs = qs.filter(computed_at__lte=at_dt)
        return qs.order_by("-computed_at", "-id").first()


class ThreatScoreManager(models.Manager):
    def get_queryset(self) -> ThreatScoreQuerySet:  # type: ignore[override]
        return ThreatScoreQuerySet(self.model, using=self._db)

    def latest_for(
        self, *, scenario_id: int, da_id: int, track_id: int, at_iso: Optional[str] = None
    ):
        return (
            self.get_queryset()
            .for_key(scenario_id=scenario_id, da_id=da_id, track_id=track_id)
            .at_or_latest(at_iso=at_iso)
        )


# tewa/models.py (inside ModelParams)

# --- ranges & timing ---
R_W_m = models.PositiveIntegerField(
    default=25000, help_text="Weapon range (m)")
R_DA_m = models.PositiveIntegerField(default=8000, help_text="DA radius (m)")
tick_s = models.FloatField(default=1.0, validators=[
                           MinValueValidator(1e-6)], help_text="Tick rate (s)")

# --- weights (must sum to 1.0 at the form/API layer) ---
w_cpa = models.FloatField(default=0.35, validators=[
                          MinValueValidator(0.0), MaxValueValidator(1.0)])
w_tcpa = models.FloatField(default=0.25, validators=[
                           MinValueValidator(0.0), MaxValueValidator(1.0)])
w_tdb = models.FloatField(default=0.20, validators=[
                          MinValueValidator(0.0), MaxValueValidator(1.0)])
w_twrp = models.FloatField(default=0.20, validators=[
                           MinValueValidator(0.0), MaxValueValidator(1.0)])

# --- sigmas (optional) ---
sigma_cpa = models.FloatField(null=True, blank=True)
sigma_tcpa = models.FloatField(null=True, blank=True)
sigma_tdb = models.FloatField(null=True, blank=True)
sigma_twrp = models.FloatField(null=True, blank=True)

# --- audit (optional if you already have updated_at/created_at via mixin) ---
updated_by = models.ForeignKey(
    getattr(settings, "AUTH_USER_MODEL", "auth.User"),
    null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_params"
)
