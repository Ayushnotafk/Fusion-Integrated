from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.gymkhana.models.clubs import Club


class MembershipApplication(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CONFIRMED = "confirmed", "Confirmed"

    club = models.ForeignKey(  # Spec: AFR-GYM-016
        Club,
        on_delete=models.PROTECT,
        related_name="membership_applications",
    )
    student_id = models.PositiveBigIntegerField()  # Spec: AFR-GYM-016
    achievements = models.TextField(blank=True)  # Spec: AFR-GYM-016
    description = models.TextField(blank=True)  # Spec: AFR-GYM-016
    status = models.CharField(  # Spec: AFR-GYM-019, BR-GYM-011
        max_length=9,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    remarks = models.TextField(blank=True)  # Spec: AFR-GYM-021

    class Meta:
        db_table = "gymkhana_membership_application"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(  # Spec: BR-GYM-011
                condition=Q(status__in=["open", "confirmed"]),
                name="gymkhana_membership_status_allowed",
            ),
        ]
        indexes = [
            models.Index(fields=["club", "status"]),
            models.Index(fields=["student_id", "status"]),
        ]

    def __str__(self):
        return f"{self.student_id} -> {self.club_id} ({self.status})"
