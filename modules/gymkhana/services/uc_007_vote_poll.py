from django.db import transaction
from django.utils import timezone

from modules.gymkhana.models import Poll, PollVote
from modules.gymkhana.services.adapters import StudentRegistry, student_registry
from modules.gymkhana.services.common import _actor_id, require_student_actor
from modules.gymkhana.services.exceptions import AlreadyVoted, PollNotAvailable


@transaction.atomic
def vote_poll(
    *,
    actor,
    poll_id: int,
    choice_id: int,
    students: StudentRegistry = student_registry,
) -> PollVote:
    # Spec: UC-GYM-007 preconditions and main flow steps 1-3, BR-GYM-013, BR-GYM-014
    student_id = require_student_actor(actor, students)
    poll = Poll.objects.select_for_update().get(pk=poll_id)
    if poll.expiration_date <= timezone.now():
        raise PollNotAvailable("The poll is not active.")
    groups = set(
        poll.target_groups.values_list("batch", "branch")
    )
    if not groups.intersection(students.groups_for_student(student_id)):
        raise PollNotAvailable("The student is not in the poll audience.")
    if PollVote.objects.filter(poll=poll, student_id=student_id).exists():
        # Spec: UC-GYM-007 exception flow, BR-GYM-015
        raise AlreadyVoted("The student has already voted in this poll.")
    if not poll.choices.filter(pk=choice_id).exists():
        raise PollNotAvailable("The selected choice is not in this poll.")
    # Spec: UC-GYM-007 main flow steps 4-5, BW-GYM-02
    return PollVote.objects.create(
        poll=poll,
        choice_id=choice_id,
        student_id=student_id,
    )


@transaction.atomic
def show_poll(*, actor, poll_id: int, students: StudentRegistry = student_registry) -> Poll:
    # Spec: UC-GYM-007 preconditions and main flow step 1, BR-GYM-014
    student_id = require_student_actor(actor, students)
    poll = Poll.objects.prefetch_related("choices", "target_groups").get(pk=poll_id)
    if poll.expiration_date <= timezone.now():
        raise PollNotAvailable("The poll is not active.")
    groups = set(poll.target_groups.values_list("batch", "branch"))
    if not groups.intersection(students.groups_for_student(student_id)):
        raise PollNotAvailable("The student is not in the poll audience.")
    return poll
