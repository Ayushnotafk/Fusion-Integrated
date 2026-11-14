from django.db import transaction

from modules.gymkhana.models import Club, MembershipApplication
from modules.gymkhana.services.adapters import StudentRegistry, student_registry
from modules.gymkhana.services.common import (
    require_confirmed_club,
    require_student_actor,
)
from modules.gymkhana.services.exceptions import DuplicateApplication


@transaction.atomic
def apply_membership(
    *,
    actor,
    club_id: int,
    achievements="",
    description="",
    students: StudentRegistry = student_registry,
):
    # Spec: UC-GYM-004 preconditions and main flow steps 1-5, BR-GYM-007
    club = Club.objects.select_for_update().get(pk=club_id)
    require_confirmed_club(club)
    student_id = require_student_actor(actor, students)
    # Spec: BR-GYM-008, BR-GYM-009, UC-GYM-004 exception flow
    if MembershipApplication.objects.filter(
        club=club, student_id=student_id
    ).exists():
        raise DuplicateApplication("A same-club application already exists.")
    # Spec: UC-GYM-004 main flow step 6, BW-GYM-01
    return MembershipApplication.objects.create(
        club=club,
        student_id=student_id,
        achievements=achievements,
        description=description,
        status=MembershipApplication.Status.OPEN,
    )


@transaction.atomic
def list_confirmed_clubs():
    # Spec: UC-GYM-004 main flow step 1
    return Club.objects.filter(status=Club.Status.CONFIRMED).order_by("name")
