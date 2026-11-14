from django.db import transaction

from modules.gymkhana.models import Club
from modules.gymkhana.services.common import require_open_club, require_student_admin


@transaction.atomic
def approve_club(*, actor, club_id: int) -> Club:
    # Spec: UC-GYM-011 preconditions
    require_student_admin(actor)
    club = Club.objects.select_for_update().get(pk=club_id)
    # Spec: UC-GYM-011 main flow steps 1-4, BR-GYM-004, BW-GYM-03
    require_open_club(club)
    club.status = Club.Status.CONFIRMED
    club.save(update_fields=["status", "updated_at"])
    return club
