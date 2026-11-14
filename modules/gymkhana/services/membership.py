from django.db import transaction

from modules.gymkhana.models import MembershipApplication
from modules.gymkhana.services.common import _actor_id, require_club_head
from modules.gymkhana.services.uc_004_apply_membership import apply_membership
from modules.gymkhana.services.uc_005_approve_membership import approve_memberships


@transaction.atomic
def apply(*, actor, club_id, achievements="", statement=""):
    # Spec: UC-GYM-004, AFR-GYM-016..019, BW-GYM-01
    return apply_membership(
        actor=actor,
        club_id=club_id,
        achievements=achievements,
        description=statement,
    )


@transaction.atomic
def my_applications(*, actor):
    # Spec: UC-GYM-004 success postcondition
    return MembershipApplication.objects.filter(
        student_id=_actor_id(actor)
    ).select_related("club").order_by("-created_at")


@transaction.atomic
def review(*, actor, application_id, decision, remarks=""):
    # Spec: UC-GYM-005, BR-GYM-010, BR-GYM-011
    application = MembershipApplication.objects.select_for_update().get(
        pk=application_id
    )
    require_club_head(application.club, actor)
    if decision != MembershipApplication.Status.CONFIRMED:
        raise ValueError("Only confirmation is in the current baseline.")
    result = approve_memberships(
        actor=actor,
        club_id=application.club_id,
        applications=[{"application_id": application_id, "remarks": remarks}],
    )
    if not result[0]["ok"]:
        raise ValueError("The membership application is not open.")
    application.refresh_from_db()
    return application


@transaction.atomic
def bulk_review(*, actor, items):
    # Spec: UC-GYM-005 alternative flow; each application is independent.
    grouped = {}
    for item in items:
        application = MembershipApplication.objects.get(pk=item["application_id"])
        grouped.setdefault(application.club_id, []).append(item)
    results = []
    for club_id, club_items in grouped.items():
        results.extend(
            approve_memberships(
                actor=actor,
                club_id=club_id,
                applications=club_items,
            )
        )
    return results
