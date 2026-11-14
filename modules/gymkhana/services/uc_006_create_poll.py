from django.db import transaction

from modules.gymkhana.models import Club, Poll, PollChoice, PollTargetGroup
from modules.gymkhana.services.adapters import (
    NotificationService,
    StudentRegistry,
    notification_service,
    student_registry,
)
from modules.gymkhana.services.common import (
    notify,
    require_club_head,
    target_recipients,
)
from modules.gymkhana.services.exceptions import InvalidPoll


@transaction.atomic
def create_poll(
    *,
    actor,
    club_id: int,
    title: str,
    description: str,
    expiration_date,
    choices,
    target_groups,
    students: StudentRegistry = student_registry,
    notifications: NotificationService = notification_service,
) -> Poll:
    # Spec: UC-GYM-006 preconditions and main flow steps 1-5, BR-GYM-010, BR-GYM-012, BR-GYM-013
    club = Club.objects.get(pk=club_id)
    require_club_head(club, actor)
    if len(choices) < 2:
        raise InvalidPoll("A poll requires at least two choices.")
    if not target_groups:
        raise InvalidPoll("A poll requires target groups.")
    # Spec: BR-GYM-013
    if any(
        not isinstance(batch, int) or batch <= 0 or not isinstance(branch, str) or not branch
        for batch, branch in target_groups
    ):
        raise InvalidPoll("Each target group must contain a batch and branch.")
    poll = Poll.objects.create(
        club=club,
        title=title,
        description=description,
        expiration_date=expiration_date,
    )
    # Spec: UC-GYM-006 main flow step 6
    PollChoice.objects.bulk_create(
        [PollChoice(poll=poll, text=text) for text in choices]
    )
    PollTargetGroup.objects.bulk_create(
        [PollTargetGroup(poll=poll, batch=batch, branch=branch)
         for batch, branch in target_groups]
    )
    # Spec: UC-GYM-006 main flow step 7, AFR-GYM-025
    recipients = target_recipients(poll_id=poll.id, student_registry=students)
    notify(notifications, recipients, "poll_created", {"poll_id": poll.id})
    return poll
