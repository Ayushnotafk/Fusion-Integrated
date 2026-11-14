from django.db import transaction

from modules.gymkhana.models import Club, EventReport
from modules.gymkhana.services.adapters import FacultyRegistry, faculty_registry
from modules.gymkhana.services.common import require_assigned_faculty


@transaction.atomic
def review_reports(
    *,
    actor,
    club_id: int,
    faculty: FacultyRegistry = faculty_registry,
):
    # Spec: UC-GYM-012 preconditions and main flow steps 1-2, BR-GYM-021
    club = Club.objects.get(pk=club_id)
    require_assigned_faculty(club, actor, faculty)
    # Spec: UC-GYM-012 main flow steps 3-4
    return EventReport.objects.filter(club=club)
