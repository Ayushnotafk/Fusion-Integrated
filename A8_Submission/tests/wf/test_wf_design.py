import json
from datetime import date, time, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from modules.gymkhana.models import (
    Club,
    MembershipApplication,
    Poll,
    PollChoice,
    PollTargetGroup,
    PollVote,
)
from modules.gymkhana.services import (
    approve_club,
    approve_memberships,
    apply_membership,
    create_club,
    create_poll,
    vote_poll,
)
from modules.gymkhana.services.exceptions import (
    AlreadyVoted,
    DuplicateApplication,
    InvalidAssignment,
    InvalidPoll,
    PollNotAvailable,
    UnauthorizedClubOperation,
)

pytestmark = pytest.mark.django_db

DESIGN = json.loads(
    (Path(__file__).resolve().parents[3] / "a8_design" / "WF_DESIGN.json").read_text(
        encoding="utf-8"
    )
)


class Registry:
    def __init__(self, students=(), groups=None):
        self.students = set(students)
        self.groups = groups or {}

    def is_valid_student(self, student_id):
        return student_id in self.students

    def groups_for_student(self, student_id):
        return set(self.groups.get(student_id, set()))

    def students_in_groups(self, groups):
        return {
            student_id
            for student_id, values in self.groups.items()
            if groups.intersection(values)
        }


def actor(user_id, *, kind="student", role=None):
    return SimpleNamespace(
        user_id=user_id,
        kind=kind,
        active_role=role,
        permissions=(),
    )


def club(*, status=Club.Status.CONFIRMED):
    number = Club.objects.count()
    return Club.objects.create(
        code=f"wf-club-{number}",
        name=f"Workflow Club {number}",
        description="Workflow club",
        coordinator_id=201,
        co_coordinator_id=202,
        faculty_councillor_id=301,
        category=Club.Category.TECHNICAL,
        status=status,
    )


def upload():
    return SimpleUploadedFile("workflow.txt", b"workflow")


def poll_fixture():
    club_obj = club()
    poll = Poll.objects.create(
        club=club_obj,
        title="Workflow poll",
        description="Vote",
        expiration_date=timezone.now() + timedelta(days=1),
    )
    choice = PollChoice.objects.create(poll=poll, text="A")
    PollChoice.objects.create(poll=poll, text="B")
    PollTargetGroup.objects.create(poll=poll, batch=2025, branch="CSE")
    registry = Registry({101}, {101: {(2025, "CSE")}})
    return poll, choice, registry


def run_scenario(test_id):
    if test_id == "BW-GYM-01-enrollment-success":
        club_obj = club()
        application = apply_membership(
            actor=actor(101),
            club_id=club_obj.id,
            students=Registry({101}),
        )
        assert application.status == MembershipApplication.Status.OPEN
        result = approve_memberships(
            actor=actor(201),
            club_id=club_obj.id,
            applications=[{"application_id": application.id}],
        )
        application.refresh_from_db()
        assert result[0]["ok"] is True
        assert application.status == MembershipApplication.Status.CONFIRMED
        return

    if test_id == "BW-GYM-01-duplicate-guard":
        club_obj = club()
        apply_membership(actor=actor(101), club_id=club_obj.id, students=Registry({101}))
        with pytest.raises(DuplicateApplication):
            apply_membership(
                actor=actor(101), club_id=club_obj.id, students=Registry({101})
            )
        assert MembershipApplication.objects.count() == 1
        return

    if test_id == "BW-GYM-01-unauthorized-approval-guard":
        club_obj = club()
        application = MembershipApplication.objects.create(
            club=club_obj, student_id=101, status=MembershipApplication.Status.OPEN
        )
        with pytest.raises(UnauthorizedClubOperation):
            approve_memberships(
                actor=actor(999),
                club_id=club_obj.id,
                applications=[{"application_id": application.id}],
            )
        application.refresh_from_db()
        assert application.status == MembershipApplication.Status.OPEN
        return

    if test_id == "BW-GYM-02-poll-participation-success":
        club_obj = club()
        poll = create_poll(
            actor=actor(201),
            club_id=club_obj.id,
            title="Workflow poll",
            description="Vote",
            expiration_date=timezone.now() + timedelta(days=1),
            choices=["A", "B"],
            target_groups=[(2025, "CSE")],
            students=Registry(groups={101: {(2025, "CSE")}}),
        )
        assert poll.choices.count() == 2
        choice = poll.choices.first()
        vote = vote_poll(
            actor=actor(101),
            poll_id=poll.id,
            choice_id=choice.id,
            students=Registry({101}, {101: {(2025, "CSE")}}),
        )
        assert vote.student_id == 101
        assert PollVote.objects.filter(poll=poll, student_id=101).count() == 1
        return

    if test_id == "BW-GYM-02-choice-guard":
        with pytest.raises(InvalidPoll):
            create_poll(
                actor=actor(201),
                club_id=club().id,
                title="Workflow poll",
                description="Vote",
                expiration_date=timezone.now() + timedelta(days=1),
                choices=["A"],
                target_groups=[(2025, "CSE")],
            )
        assert Poll.objects.count() == 0
        return

    if test_id == "BW-GYM-02-target-guard":
        with pytest.raises(InvalidPoll):
            create_poll(
                actor=actor(201),
                club_id=club().id,
                title="Workflow poll",
                description="Vote",
                expiration_date=timezone.now() + timedelta(days=1),
                choices=["A", "B"],
                target_groups=[(0, "")],
            )
        assert Poll.objects.count() == 0
        return

    if test_id == "BW-GYM-02-vote-eligibility-guard":
        poll, choice, registry = poll_fixture()
        poll.expiration_date = timezone.now() - timedelta(seconds=1)
        poll.save(update_fields=["expiration_date"])
        with pytest.raises(PollNotAvailable):
            vote_poll(
                actor=actor(101),
                poll_id=poll.id,
                choice_id=choice.id,
                students=registry,
            )
        assert PollVote.objects.count() == 0
        return

    if test_id == "BW-GYM-02-duplicate-vote-guard":
        poll, choice, registry = poll_fixture()
        vote_poll(
            actor=actor(101), poll_id=poll.id, choice_id=choice.id, students=registry
        )
        with pytest.raises(AlreadyVoted):
            vote_poll(
                actor=actor(101), poll_id=poll.id, choice_id=choice.id, students=registry
            )
        assert PollVote.objects.count() == 1
        return

    if test_id == "BW-GYM-03-establishment-success":
        result = create_club(
            actor=actor(1, kind="staff", role="student_admin"),
            name="Established Club",
            description="Workflow club",
            category=Club.Category.TECHNICAL,
            coordinator_id=101,
            co_coordinator_id=102,
            faculty_councillor_id=301,
            students=Registry({101, 102}),
        )
        assert result.status == Club.Status.OPEN
        result = approve_club(
            actor=actor(1, kind="staff", role="student_admin"),
            club_id=result.id,
        )
        assert result.status == Club.Status.CONFIRMED
        return

    if test_id == "BW-GYM-03-creation-guard":
        with pytest.raises(InvalidAssignment):
            create_club(
                actor=actor(1, kind="staff", role="student_admin"),
                name="Invalid Club",
                description="Workflow club",
                category=Club.Category.TECHNICAL,
                coordinator_id=0,
                co_coordinator_id=102,
                faculty_councillor_id=301,
                students=Registry({102}),
            )
        assert Club.objects.count() == 0
        return

    if test_id == "BW-GYM-03-approval-guard":
        club_obj = club(status=Club.Status.CONFIRMED)
        with pytest.raises(UnauthorizedClubOperation):
            approve_club(
                actor=actor(1, kind="staff", role="student_admin"),
                club_id=club_obj.id,
            )
        club_obj.refresh_from_db()
        assert club_obj.status == Club.Status.CONFIRMED
        return

    raise AssertionError(f"Unhandled frozen workflow scenario: {test_id}")


@pytest.mark.parametrize(
    "scenario",
    DESIGN,
    ids=[f"{item['test_id']}__{item['source_id']}" for item in DESIGN],
)
def test_frozen_workflow_scenario(scenario):
    """Each test maps directly to one frozen workflow test_id/source_id."""
    run_scenario(scenario["test_id"])
