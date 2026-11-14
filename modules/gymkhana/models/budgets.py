from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.gymkhana.models.clubs import Club


class BudgetRequest(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"

    club = models.ForeignKey(  # Spec: AFR-GYM-029
        Club,
        on_delete=models.PROTECT,
        related_name="budget_requests",
    )
    purpose = models.CharField(max_length=240)  # Spec: AFR-GYM-029
    amount = models.DecimalField(  # Spec: AFR-GYM-030, BR-GYM-017
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    supporting_file = models.FileField(  # Spec: AFR-GYM-030, BR-GYM-018
        upload_to="gymkhana/budget-requests/",
    )
    description = models.TextField(blank=True)  # Spec: AFR-GYM-029
    status = models.CharField(  # Spec: AFR-GYM-031
        max_length=4,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    class Meta:
        db_table = "gymkhana_budget_request"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(  # Spec: BR-GYM-017
                condition=Q(amount__gte=0),
                name="gymkhana_budget_amount_non_negative",
            ),
            models.CheckConstraint(  # Spec: AFR-GYM-031, BR-GYM-018
                condition=Q(status="open"),
                name="gymkhana_budget_status_open",
            ),
        ]

    def __str__(self):
        return f"{self.club_id}: {self.purpose}"
