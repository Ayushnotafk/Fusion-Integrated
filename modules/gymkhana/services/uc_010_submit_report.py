from django.db import transaction

from modules.gymkhana.models import Club, EventReport
from modules.gymkhana.services.adapters import StudentRegistry, student_registry
from modules.gymkhana.services.common import (
    require_club_head,
    require_confirmed_club,
    require_student,
)
from modules.gymkhana.services.exceptions import InvalidReference, MissingRequiredFile


@transaction.atomic
def submit_report(
    *,
    actor,
    club_id: int,
    student_incharge_id: int,
    event_name: str,
    event_date,
    start_time,
    end_time,
    description: str,
    report_file,
    students: StudentRegistry = student_registry,
) -> EventReport:
    # Spec: UC-GYM-010 preconditions, BR-GYM-010
    club = Club.objects.get(pk=club_id)
    require_club_head(club, actor)
    require_confirmed_club(club)
    if not student_incharge_id or not event_name:
        # Spec: UC-GYM-010 exception flow
        raise InvalidReference("Required report references are missing.")
    # Spec: AFR-GYM-032, BR-GYM-001
    require_student(student_incharge_id, students)
    if report_file is None:
        # Spec: UC-GYM-010 exception flow, BR-GYM-019
        raise MissingRequiredFile("A report/details file is required.")
    # Spec: UC-GYM-010 main flow steps 1-6, AFR-GYM-032
    return EventReport.objects.create(
        club=club,
        student_incharge_id=student_incharge_id,
        event_name=event_name,
        event_date=event_date,
        start_time=start_time,
        end_time=end_time,
        description=description,
        report_file=report_file,
    )
