from django.db import models

from core.db.mixins import TimeStampedModel
from modules.gymkhana.models.clubs import Club


class Poll(TimeStampedModel):
    club = models.ForeignKey(  # Spec: AFR-GYM-023
        Club,
        on_delete=models.PROTECT,
        related_name="polls",
    )
    title = models.CharField(max_length=160)  # Spec: AFR-GYM-023
    description = models.TextField(blank=True)  # Spec: AFR-GYM-023
    expiration_date = models.DateTimeField()  # Spec: AFR-GYM-024

    class Meta:
        db_table = "gymkhana_poll"
        ordering = ["expiration_date"]

    def __str__(self):
        return self.title


class PollChoice(TimeStampedModel):
    poll = models.ForeignKey(  # Spec: BR-GYM-012
        Poll,
        on_delete=models.CASCADE,
        related_name="choices",
    )
    text = models.CharField(max_length=240)  # Spec: BR-GYM-012

    class Meta:
        db_table = "gymkhana_poll_choice"
        ordering = ["id"]

    def __str__(self):
        return self.text


class PollTargetGroup(TimeStampedModel):
    poll = models.ForeignKey(  # Spec: BR-GYM-013
        Poll,
        on_delete=models.CASCADE,
        related_name="target_groups",
    )
    batch = models.PositiveIntegerField()  # Spec: BR-GYM-013
    branch = models.CharField(max_length=120)  # Spec: BR-GYM-013

    class Meta:
        db_table = "gymkhana_poll_target_group"
        constraints = [
            models.UniqueConstraint(  # Spec: BR-GYM-013
                fields=["poll", "batch", "branch"],
                name="gymkhana_unique_poll_target_group",
            ),
        ]

    def __str__(self):
        return f"{self.poll_id}:{self.batch}:{self.branch}"


class PollVote(TimeStampedModel):
    poll = models.ForeignKey(  # Spec: BR-GYM-015
        Poll,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    choice = models.ForeignKey(  # Spec: BR-GYM-015
        PollChoice,
        on_delete=models.PROTECT,
        related_name="votes",
    )
    student_id = models.PositiveBigIntegerField()  # Spec: BR-GYM-015

    class Meta:
        db_table = "gymkhana_poll_vote"
        constraints = [
            models.UniqueConstraint(  # Spec: BR-GYM-015
                fields=["poll", "student_id"],
                name="gymkhana_one_vote_per_student_poll",
            ),
        ]

    def __str__(self):
        return f"{self.student_id} -> {self.poll_id}"
