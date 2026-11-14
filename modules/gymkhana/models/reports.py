from django.db import models

from core.db.mixins import TimeStampedModel
from modules.gymkhana.models.clubs import Club


class EventReport(TimeStampedModel):
    club = models.ForeignKey(  # Spec: AFR-GYM-034
        Club,
        on_delete=models.PROTECT,
        related_name="event_reports",
    )
    student_incharge_id = models.PositiveBigIntegerField()  # Spec: AFR-GYM-034
    event_name = models.CharField(max_length=160)  # Spec: AFR-GYM-034
    event_date = models.DateField()  # Spec: AFR-GYM-034
    start_time = models.TimeField()  # Spec: AFR-GYM-034
    end_time = models.TimeField()  # Spec: AFR-GYM-034
    description = models.TextField()  # Spec: AFR-GYM-034
    report_file = models.FileField(  # Spec: AFR-GYM-033, BR-GYM-019
        upload_to="gymkhana/event-reports/",
    )

    class Meta:
        db_table = "gymkhana_event_report"
        ordering = ["-event_date", "start_time"]

    def __str__(self):
        return self.event_name
