from django.db import transaction

from modules.gymkhana.models import Club, MembershipApplication
from modules.gymkhana.services.common import require_club_head


@transaction.atomic
def list_pending_memberships(*, actor, club_id: int):
    # Spec: UC-GYM-005 main flow step 1, AFR-GYM-020, BR-GYM-010
    club = Club.objects.get(pk=club_id)
    require_club_head(club, actor)
    return MembershipApplication.objects.filter(
        club=club,
        status=MembershipApplication.Status.OPEN,
    )


@transaction.atomic
def approve_memberships(*, actor, club_id: int, applications):
    # Spec: UC-GYM-005 preconditions, BR-GYM-010
    club = Club.objects.get(pk=club_id)
    reviewer_id = require_club_head(club, actor)
    results = []
    for item in applications:
        # Spec: UC-GYM-005 alternative/exception flow, independent evaluation
        application = MembershipApplication.objects.select_for_update().filter(
            pk=item["application_id"], club=club
        ).first()
        if application is None or application.status != MembershipApplication.Status.OPEN:
            results.append({"application_id": item["application_id"], "ok": False})
            continue
        # Spec: UC-GYM-005 main flow steps 2-5, BR-GYM-011, BW-GYM-01
        application.status = MembershipApplication.Status.CONFIRMED
        application.remarks = item.get("remarks", "")
        application.save(update_fields=["status", "remarks", "updated_at"])
        results.append({"application_id": application.id, "ok": True, "reviewed_by": reviewer_id})
    return results
