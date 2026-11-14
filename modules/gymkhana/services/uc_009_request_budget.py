from decimal import Decimal

from django.db import transaction

from modules.gymkhana.models import BudgetRequest, Club
from modules.gymkhana.services.common import require_club_head, require_confirmed_club
from modules.gymkhana.services.exceptions import InvalidReference, MissingRequiredFile


@transaction.atomic
def request_budget(
    *,
    actor,
    club_id: int,
    purpose: str,
    amount,
    supporting_file,
    description: str,
) -> BudgetRequest:
    # Spec: UC-GYM-009 preconditions, BR-GYM-010
    club = Club.objects.get(pk=club_id)
    require_club_head(club, actor)
    require_confirmed_club(club)
    if supporting_file is None:
        # Spec: UC-GYM-009 exception flow, BR-GYM-018
        raise MissingRequiredFile("A supporting file is required.")
    # Spec: BR-GYM-017
    if Decimal(str(amount)) < 0:
        raise InvalidReference("Budget amount must be non-negative.")
    # Spec: UC-GYM-009 main flow, BR-GYM-018, AFR-GYM-031
    return BudgetRequest.objects.create(
        club=club,
        purpose=purpose,
        amount=amount,
        supporting_file=supporting_file,
        description=description,
        status=BudgetRequest.Status.OPEN,
    )
