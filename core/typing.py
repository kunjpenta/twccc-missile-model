# core/typing.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from typing import NewType, TypedDict

ScenarioId = NewType("ScenarioId", int)
TrackPK = NewType("TrackPK", int)
DefendedAssetPK = NewType("DefendedAssetPK", int)


class ScoreRow(TypedDict, total=False):
    track_id: str
    da_name: str
    score: float
    computed_at: str


# core/models.py


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('operator', 'Operator'),
        ('viewer', 'Viewer'),
    ]
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default='viewer')

    def __str__(self):
        return f"{self.username} ({self.role})"
