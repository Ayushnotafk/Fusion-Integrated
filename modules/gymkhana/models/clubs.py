from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class Club(TimeStampedModel):
    class Category(models.TextChoices):
        TECHNICAL = "Technical", "Technical"
        SPORTS = "Sports", "Sports"
        CULTURAL = "Cultural", "Cultural"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CONFIRMED = "confirmed", "Confirmed"

    code = models.SlugField(max_length=60, unique=True)  # Spec: CFR-GYM-001
    name = models.CharField(max_length=120)  # Spec: CFR-GYM-001
    description = models.TextField(blank=True)  # Spec: CFR-GYM-001
    coordinator_id = models.PositiveBigIntegerField()  # Spec: AFR-GYM-001
    co_coordinator_id = models.PositiveBigIntegerField()  # Spec: AFR-GYM-002
    faculty_councillor_id = models.PositiveBigIntegerField()  # Spec: AFR-GYM-003
    category = models.CharField(  # Spec: AFR-GYM-004
        max_length=20,
        choices=Category.choices,
    )
    status = models.CharField(  # Spec: AFR-GYM-005, BR-GYM-004
        max_length=9,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    class Meta:
        db_table = "gymkhana_club"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(  # Spec: BR-GYM-003
                condition=Q(category__in=["Technical", "Sports", "Cultural"]),
                name="gymkhana_club_category_allowed",
            ),
            models.CheckConstraint(  # Spec: BR-GYM-004
                condition=Q(status__in=["open", "confirmed"]),
                name="gymkhana_club_status_allowed",
            ),
        ]

    def __str__(self):
        return self.name


class ClubLeadershipDesignation(TimeStampedModel):
    class Role(models.TextChoices):
        COORDINATOR = "coordinator", "Coordinator"
        HEAD = "head", "Club Head"
        CO_COORDINATOR = "co_coordinator", "Co-Coordinator"

    club = models.ForeignKey(  # Spec: AFR-GYM-007, BR-GYM-016
        Club,
        on_delete=models.CASCADE,
        related_name="leadership_designations",
    )
    student_id = models.PositiveBigIntegerField()  # Spec: BR-GYM-001
    role = models.CharField(  # Spec: AFR-GYM-007
        max_length=20,
        choices=Role.choices,
    )
    is_active = models.BooleanField(default=True)  # Spec: BR-GYM-016

    class Meta:
        db_table = "gymkhana_leadership_designation"
        constraints = [
            models.CheckConstraint(  # Spec: BR-GYM-016
                condition=Q(role__in=["coordinator", "co_coordinator", "head"]),
                name="gymkhana_leadership_designation_allowed",
            ),
            models.UniqueConstraint(  # Spec: BR-GYM-016
                fields=["club", "role"],
                condition=Q(is_active=True),
                name="gymkhana_one_current_leader_per_designation",
            ),
        ]
        indexes = [
            models.Index(fields=["club", "is_active"]),
            models.Index(fields=["student_id", "is_active"]),
        ]

    def __str__(self):
        return f"{self.club_id}:{self.role}:{self.student_id}"


class Venue(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)  # Spec: BR-GYM-020
    is_configured = models.BooleanField(default=True)  # Spec: BR-GYM-020

    class Meta:
        db_table = "gymkhana_venue"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ClubSession(TimeStampedModel):
    club = models.ForeignKey(  # Spec: AFR-GYM-010
        Club,
        on_delete=models.PROTECT,
        related_name="sessions",
    )
    venue = models.ForeignKey(  # Spec: AFR-GYM-011, BR-GYM-020
        Venue,
        on_delete=models.PROTECT,
        related_name="sessions",
    )
    booking_date = models.DateField()  # Spec: AFR-GYM-011
    start_time = models.TimeField()  # Spec: AFR-GYM-012, BR-GYM-005
    end_time = models.TimeField()  # Spec: AFR-GYM-012, BR-GYM-005
    description = models.TextField()  # Spec: AFR-GYM-010
    poster = models.FileField(  # Spec: AFR-GYM-013
        upload_to="gymkhana/posters/",
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "gymkhana_session"
        ordering = ["booking_date", "start_time"]
        constraints = [
            models.CheckConstraint(  # Spec: BR-GYM-005
                condition=Q(start_time__lt=models.F("end_time")),
                name="gymkhana_session_start_before_end",
            ),
        ]

    def __str__(self):
        return f"{self.club} session on {self.booking_date}"


class ClubEvent(TimeStampedModel):
    club = models.ForeignKey(  # Spec: AFR-GYM-014
        Club,
        on_delete=models.PROTECT,
        related_name="events",
    )
    name = models.CharField(max_length=160)  # Spec: AFR-GYM-014
    venue = models.ForeignKey(  # Spec: AFR-GYM-015, BR-GYM-020
        Venue,
        on_delete=models.PROTECT,
        related_name="events",
    )
    booking_date = models.DateField()  # Spec: AFR-GYM-015
    start_time = models.TimeField()  # Spec: AFR-GYM-012, BR-GYM-005
    end_time = models.TimeField()  # Spec: AFR-GYM-012, BR-GYM-005
    description = models.TextField()  # Spec: AFR-GYM-014
    poster = models.FileField(  # Spec: AFR-GYM-015
        upload_to="gymkhana/posters/",
        blank=True,
        null=True,
    )
    faculty_id = models.PositiveBigIntegerField()  # Spec: AFR-GYM-014

    class Meta:
        db_table = "gymkhana_event"
        ordering = ["booking_date", "start_time"]
        constraints = [
            models.CheckConstraint(  # Spec: BR-GYM-005
                condition=Q(start_time__lt=models.F("end_time")),
                name="gymkhana_event_start_before_end",
            ),
        ]

    def __str__(self):
        return self.name
