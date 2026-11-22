import json
from datetime import date, time, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from modules.gymkhana.models import (
    Club,
    ClubEvent,
    ClubLeadershipDesignation,
    ClubSession,
    EventReport,
    MembershipApplication,
    Poll,
    PollChoice,
    PollTargetGroup,
    PollVote,
    Venue,
)
from modules.gymkhana.services import (
    approve_club,
    approve_memberships,
    apply_membership,
    book_event,
    book_session,
    change_leadership,
    create_club,
    create_poll,
    request_budget,
    review_reports,
    show_poll,
    submit_report,
    vote_poll,
)
from modules.gymkhana.services.exceptions import (
    AlreadyVoted,
    BookingConflict,
    DuplicateApplication,
    InvalidAssignment,
    InvalidPoll,
    InvalidReference,
    InvalidTimeRange,
    MissingRequiredFile,
    PollNotAvailable,
    UnauthorizedClubOperation,
    VenueUnavailable,
)

pytestmark = pytest.mark.django_db

DESIGN = json.loads(
    (Path(__file__).resolve().parents[3] / "a8_design" / "FR_DESIGN.json").read_text(
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


class Notifications:
    def __init__(self):
        self.calls = []

    def notify(self, *, recipients, event, payload):
        self.calls.append((set(recipients), event, payload))


def actor(user_id, *, kind="student", role=None):
    return SimpleNamespace(
        user_id=user_id, kind=kind, active_role=role, permissions=()
    )


def upload(name="evidence.txt"):
    return SimpleUploadedFile(name, b"evidence", content_type="text/plain")


def club(*, status=Club.Status.CONFIRMED):
    number = Club.objects.count()
    return Club.objects.create(
        code=f"fr-club-{number}",
        name=f"FR Club {number}",
        description="Functional requirement club",
        coordinator_id=201,
        co_coordinator_id=202,
        faculty_councillor_id=301,
        category=Club.Category.TECHNICAL,
        status=status,
    )


def leadership(club_obj, coordinator=201, co_coordinator=202):
    ClubLeadershipDesignation.objects.bulk_create(
        [
            ClubLeadershipDesignation(
                club=club_obj,
                student_id=coordinator,
                role=ClubLeadershipDesignation.Role.COORDINATOR,
            ),
            ClubLeadershipDesignation(
                club=club_obj,
                student_id=co_coordinator,
                role=ClubLeadershipDesignation.Role.CO_COORDINATOR,
            ),
        ]
    )


def poll_fixture():
    club_obj = club()
    poll = Poll.objects.create(
        club=club_obj,
        title="FR poll",
        description="Choose",
        expiration_date=timezone.now() + timedelta(days=1),
    )
    choice = PollChoice.objects.create(poll=poll, text="A")
    PollChoice.objects.create(poll=poll, text="B")
    PollTargetGroup.objects.create(poll=poll, batch=2025, branch="CSE")
    registry = Registry({101}, {101: {(2025, "CSE")}})
    return poll, choice, registry


def run_scenario(test_id):
    if test_id == "CFR-GYM-001-minimum":
        result = create_club(
            actor=actor(1, kind="staff", role="student_admin"),
            name="CFR Club",
            description="Description",
            category=Club.Category.TECHNICAL,
            coordinator_id=101,
            co_coordinator_id=102,
            faculty_councillor_id=301,
            students=Registry({101, 102}),
        )
        assert result.status == Club.Status.OPEN
        assert approve_club(
            actor=actor(1, kind="staff", role="student_admin"), club_id=result.id
        ).status == Club.Status.CONFIRMED
        return

    if test_id == "CFR-GYM-002-minimum":
        club_obj = club()
        leadership(club_obj)
        result = change_leadership(
            actor=actor(201),
            club_id=club_obj.id,
            coordinator_id=301,
            co_coordinator_id=302,
            students=Registry({301, 302}),
        )
        assert (result.coordinator_id, result.co_coordinator_id) == (301, 302)
        assert ClubLeadershipDesignation.objects.filter(
            club=club_obj, is_active=True
        ).count() == 2
        return

    if test_id == "CFR-GYM-003-minimum":
        club_obj = club()
        venue = Venue.objects.create(name="CFR Venue")
        notifications = Notifications()
        session = book_session(
            actor=actor(201),
            club_id=club_obj.id,
            venue_id=venue.id,
            booking_date=date.today(),
            start_time=time(10),
            end_time=time(11),
            description="Session",
            notifications=notifications,
        )
        event = book_event(
            actor=actor(201),
            club_id=club_obj.id,
            name="Event",
            venue_id=venue.id,
            booking_date=date.today(),
            start_time=time(11),
            end_time=time(12),
            description="Event",
            faculty_id=301,
            notifications=notifications,
        )
        assert session.club_id == event.club_id == club_obj.id
        assert len(notifications.calls) == 2
        return

    if test_id == "CFR-GYM-004-minimum":
        club_obj = club()
        application = apply_membership(
            actor=actor(101),
            club_id=club_obj.id,
            achievements="Achievements",
            description="Statement",
            students=Registry({101}),
        )
        assert application.status == MembershipApplication.Status.OPEN
        result = approve_memberships(
            actor=actor(201),
            club_id=club_obj.id,
            applications=[{"application_id": application.id, "remarks": "Approved"}],
        )
        application.refresh_from_db()
        assert result[0]["ok"] is True
        assert application.status == MembershipApplication.Status.CONFIRMED
        assert application.remarks == "Approved"
        return

    if test_id == "CFR-GYM-005-minimum":
        club_obj = club()
        notifications = Notifications()
        poll = create_poll(
            actor=actor(201),
            club_id=club_obj.id,
            title="Poll",
            description="Question",
            expiration_date=timezone.now() + timedelta(days=1),
            choices=["A", "B"],
            target_groups=[(2025, "CSE")],
            students=Registry(groups={101: {(2025, "CSE")}}),
            notifications=notifications,
        )
        choice = poll.choices.first()
        assert len(notifications.calls) == 1
        assert show_poll(
            actor=actor(101),
            poll_id=poll.id,
            students=Registry({101}, {101: {(2025, "CSE")}}),
        ).id == poll.id
        vote_poll(
            actor=actor(101),
            poll_id=poll.id,
            choice_id=choice.id,
            students=Registry({101}, {101: {(2025, "CSE")}}),
        )
        assert PollVote.objects.filter(poll=poll, student_id=101).count() == 1
        return

    if test_id == "CFR-GYM-006-minimum":
        result = request_budget(
            actor=actor(201),
            club_id=club().id,
            purpose="Equipment",
            amount=10,
            supporting_file=upload(),
            description="Budget request",
        )
        assert result.status == "open"
        return

    if test_id == "CFR-GYM-007-minimum":
        club_obj = club()
        result = submit_report(
            actor=actor(201),
            club_id=club_obj.id,
            student_incharge_id=101,
            event_name="Event",
            event_date=date.today(),
            start_time=time(10),
            end_time=time(11),
            description="Report",
            report_file=upload(),
            students=Registry({101}),
        )
        assert result.club_id == club_obj.id
        assert list(review_reports(actor=actor(301, kind="faculty"), club_id=club_obj.id)) == [result]
        return

    if test_id == "AFR-GYM-001-minimum":
        result = create_club(
            actor=actor(1, kind="staff", role="student_admin"),
            name="All Fields",
            description="Description",
            category=Club.Category.TECHNICAL,
            coordinator_id=101,
            co_coordinator_id=102,
            faculty_councillor_id=301,
            students=Registry({101, 102}),
        )
        assert (result.name, result.description, result.category) == (
            "All Fields",
            "Description",
            Club.Category.TECHNICAL,
        )
        assert (result.coordinator_id, result.co_coordinator_id, result.faculty_councillor_id) == (101, 102, 301)
        return

    if test_id.startswith("AFR-GYM-002-"):
        invalid = 101 if test_id.endswith("coordinator") else 102
        if test_id.endswith("co-coordinator"):
            kwargs = {"coordinator_id": 101, "co_coordinator_id": 0}
        else:
            kwargs = {"coordinator_id": 0, "co_coordinator_id": 102}
        with pytest.raises(InvalidAssignment):
            create_club(
                actor=actor(1, kind="staff", role="student_admin"),
                name="Invalid",
                description="Description",
                category=Club.Category.TECHNICAL,
                faculty_councillor_id=301,
                students=Registry({invalid}),
                **kwargs,
            )
        return

    if test_id == "AFR-GYM-003-minimum":
        result = create_club(
            actor=actor(1, kind="staff", role="student_admin"),
            name="Faculty",
            description="Description",
            category=Club.Category.TECHNICAL,
            coordinator_id=101,
            co_coordinator_id=102,
            faculty_councillor_id=301,
            students=Registry({101, 102}),
        )
        assert result.faculty_councillor_id == 301
        return

    if test_id == "AFR-GYM-004-minimum":
        for category in Club.Category.values:
            result = create_club(
                actor=actor(1, kind="staff", role="student_admin"),
                name=f"Category {category}",
                description="Description",
                category=category,
                coordinator_id=101,
                co_coordinator_id=102,
                faculty_councillor_id=301,
                students=Registry({101, 102}),
            )
            assert result.category == category
        return

    if test_id == "AFR-GYM-005-minimum":
        assert create_club(
            actor=actor(1, kind="staff", role="student_admin"),
            name="Open",
            description="Description",
            category=Club.Category.TECHNICAL,
            coordinator_id=101,
            co_coordinator_id=102,
            faculty_councillor_id=301,
            students=Registry({101, 102}),
        ).status == Club.Status.OPEN
        return

    if test_id == "AFR-GYM-006-minimum":
        club_obj = club(status=Club.Status.OPEN)
        assert approve_club(
            actor=actor(1, kind="staff", role="student_admin"), club_id=club_obj.id
        ).status == Club.Status.CONFIRMED
        return

    if test_id.startswith("AFR-GYM-007"):
        club_obj = club()
        leadership(club_obj)
        result = change_leadership(
            actor=actor(201),
            club_id=club_obj.id,
            coordinator_id=301,
            co_coordinator_id=302,
            students=Registry({301, 302}),
        )
        assert (result.coordinator_id, result.co_coordinator_id) == (301, 302)
        return

    if test_id.startswith("AFR-GYM-008-"):
        club_obj = club()
        leadership(club_obj)
        kwargs = (
            {"coordinator_id": 0, "co_coordinator_id": 302}
            if test_id.endswith("coordinator")
            else {"coordinator_id": 301, "co_coordinator_id": 0}
        )
        with pytest.raises(InvalidAssignment):
            change_leadership(
                actor=actor(201),
                club_id=club_obj.id,
                students=Registry({301, 302}),
                **kwargs,
            )
        club_obj.refresh_from_db()
        assert (club_obj.coordinator_id, club_obj.co_coordinator_id) == (201, 202)
        return

    if test_id == "AFR-GYM-009-minimum":
        club_obj = club()
        leadership(club_obj)
        change_leadership(
            actor=actor(201),
            club_id=club_obj.id,
            coordinator_id=301,
            co_coordinator_id=302,
            students=Registry({301, 302}),
        )
        current = ClubLeadershipDesignation.objects.filter(club=club_obj, is_active=True)
        assert set(current.values_list("student_id", flat=True)) == {301, 302}
        return

    if test_id.startswith("AFR-GYM-010") or test_id.startswith("AFR-GYM-013"):
        club_obj = club()
        venue = Venue.objects.create(name="Session Venue")
        notifications = Notifications()
        result = book_session(
            actor=actor(201),
            club_id=club_obj.id,
            venue_id=venue.id,
            booking_date=date.today(),
            start_time=time(10),
            end_time=time(11),
            description="Session",
            poster=upload("poster.txt"),
            notifications=notifications,
        )
        assert result.club_id == club_obj.id
        if test_id.startswith("AFR-GYM-013"):
            assert notifications.calls
        return

    if test_id.startswith("AFR-GYM-011-"):
        club_obj = club()
        venue = Venue.objects.create(name="Time Venue")
        event = test_id.startswith("AFR-GYM-011-event")
        kwargs = dict(
            actor=actor(201),
            club_id=club_obj.id,
            venue_id=venue.id,
            booking_date=date.today(),
            start_time=time(10),
            end_time=time(11),
            description="Booking",
        )
        if event:
            kwargs.update(name="Event", faculty_id=301)
            operation = book_event
        else:
            operation = book_session
        if "equal" in test_id:
            kwargs["end_time"] = kwargs["start_time"]
        elif "later" in test_id:
            kwargs["start_time"], kwargs["end_time"] = time(12), time(11)
        result = operation(**kwargs) if "valid" in test_id else None
        if "valid" in test_id:
            assert result is not None
        else:
            with pytest.raises(InvalidTimeRange):
                operation(**kwargs)
        return

    if test_id.startswith("AFR-GYM-012-"):
        club_obj = club()
        venue = Venue.objects.create(name="Overlap Venue")
        existing_session = "session-session" in test_id or "session-event" in test_id
        if existing_session:
            ClubSession.objects.create(
                club=club_obj, venue=venue, booking_date=date.today(),
                start_time=time(10), end_time=time(11), description="Existing",
            )
        else:
            ClubEvent.objects.create(
                club=club_obj, name="Existing", venue=venue,
                booking_date=date.today(), start_time=time(10), end_time=time(11),
                description="Existing", faculty_id=301,
            )
        kwargs = dict(
            actor=actor(201), club_id=club_obj.id, venue_id=venue.id,
            booking_date=date.today(), start_time=time(10, 30),
            end_time=time(11, 30), description="New",
        )
        if "event-event" in test_id or "session-event" in test_id:
            kwargs.update(name="New", faculty_id=301)
            operation = book_event
        else:
            operation = book_session
        with pytest.raises(BookingConflict):
            operation(**kwargs)
        return

    if test_id.startswith("AFR-GYM-014"):
        club_obj = club()
        venue = Venue.objects.create(name="Event Venue")
        notifications = Notifications()
        result = book_event(
            actor=actor(201), club_id=club_obj.id, name="Event", venue_id=venue.id,
            booking_date=date.today(), start_time=time(10), end_time=time(11),
            description="Event", faculty_id=301, poster=upload("poster.txt"),
            notifications=notifications,
        )
        assert result.name == "Event"
        return

    if test_id.startswith("AFR-GYM-015"):
        club_obj = club()
        venue = Venue.objects.create(name="Event Notification Venue")
        notifications = Notifications()
        book_event(
            actor=actor(201), club_id=club_obj.id, name="Event", venue_id=venue.id,
            booking_date=date.today(), start_time=time(10), end_time=time(11),
            description="Event", faculty_id=301, notifications=notifications,
        )
        assert notifications.calls
        return

    if test_id == "AFR-GYM-016-minimum":
        result = apply_membership(
            actor=actor(101), club_id=club().id,
            achievements="Achievements", description="Statement",
            students=Registry({101}),
        )
        assert result.status == MembershipApplication.Status.OPEN
        assert result.description == "Statement"
        return

    if test_id == "AFR-GYM-017-minimum":
        first, second = club(), club()
        apply_membership(actor=actor(101), club_id=first.id, students=Registry({101}))
        apply_membership(actor=actor(101), club_id=second.id, students=Registry({101}))
        assert MembershipApplication.objects.filter(student_id=101).count() == 2
        return

    if test_id == "AFR-GYM-018-minimum":
        club_obj = club()
        first = apply_membership(actor=actor(101), club_id=club_obj.id, students=Registry({101}))
        with pytest.raises(DuplicateApplication):
            apply_membership(actor=actor(101), club_id=club_obj.id, students=Registry({101}))
        first.refresh_from_db()
        assert MembershipApplication.objects.count() == 1
        assert first.status == MembershipApplication.Status.OPEN
        return

    if test_id == "AFR-GYM-019-minimum":
        result = approve_memberships(
            actor=actor(201), club_id=club().id,
            applications=[],
        )
        assert result == []
        return

    if test_id == "AFR-GYM-020-minimum":
        own, other = club(), club()
        first = MembershipApplication.objects.create(
            club=own, student_id=101, status=MembershipApplication.Status.OPEN
        )
        MembershipApplication.objects.create(
            club=other, student_id=102, status=MembershipApplication.Status.OPEN
        )
        result = approve_memberships(
            actor=actor(201), club_id=own.id,
            applications=[{"application_id": first.id}],
        )
        assert result[0]["application_id"] == first.id
        return

    if test_id.startswith("AFR-GYM-02") and False:
        raise AssertionError("unreachable")

    if test_id in {"AFR-GYM-021-minimum", "AFR-GYM-022-minimum"}:
        club_obj = club()
        application = MembershipApplication.objects.create(
            club=club_obj, student_id=101, status=MembershipApplication.Status.OPEN
        )
        result = approve_memberships(
            actor=actor(201), club_id=club_obj.id,
            applications=[{"application_id": application.id, "remarks": "Approved"}],
        )
        application.refresh_from_db()
        assert result[0]["ok"] is True
        assert application.status == MembershipApplication.Status.CONFIRMED
        if test_id.endswith("021-minimum"):
            assert application.remarks == "Approved"
        return

    if test_id == "AFR-GYM-023-minimum":
        poll = create_poll(
            actor=actor(201), club_id=club().id, title="Poll",
            description="Question", expiration_date=timezone.now() + timedelta(days=1),
            choices=["A", "B"], target_groups=[(2025, "CSE")],
        )
        assert poll.title == "Poll"
        assert poll.choices.count() == 2
        assert poll.target_groups.count() == 1
        return

    if test_id == "AFR-GYM-024-minimum":
        assert create_poll(
            actor=actor(201), club_id=club().id, title="Poll",
            description="Question", expiration_date=timezone.now() + timedelta(days=1),
            choices=["A", "B"], target_groups=[(2025, "CSE")],
        ).choices.count() == 2
        return

    if test_id == "AFR-GYM-025-minimum":
        notifications = Notifications()
        create_poll(
            actor=actor(201), club_id=club().id, title="Poll",
            description="Question", expiration_date=timezone.now() + timedelta(days=1),
            choices=["A", "B"], target_groups=[(2025, "CSE")],
            students=Registry(groups={101: {(2025, "CSE")}}),
            notifications=notifications,
        )
        assert notifications.calls
        return

    if test_id == "AFR-GYM-026-minimum":
        poll, _, registry = poll_fixture()
        assert show_poll(actor=actor(101), poll_id=poll.id, students=registry).choices.count() == 2
        return

    if test_id in {"AFR-GYM-027-minimum", "AFR-GYM-028-minimum"}:
        poll, choice, registry = poll_fixture()
        before = PollVote.objects.filter(choice=choice).count()
        vote_poll(actor=actor(101), poll_id=poll.id, choice_id=choice.id, students=registry)
        choice.refresh_from_db()
        assert PollVote.objects.filter(choice=choice).count() == before + 1
        assert PollVote.objects.filter(poll=poll, student_id=101).exists()
        return

    if test_id == "AFR-GYM-029-minimum":
        result = request_budget(
            actor=actor(201), club_id=club().id, purpose="Equipment",
            amount=10, supporting_file=upload(), description="Request",
        )
        assert result.amount == 10
        return

    if test_id.startswith("AFR-GYM-030-"):
        if test_id.endswith("negative-amount-rejected"):
            with pytest.raises(InvalidReference):
                request_budget(
                    actor=actor(201), club_id=club().id, purpose="Equipment",
                    amount=-1, supporting_file=upload(), description="Request",
                )
        else:
            with pytest.raises(MissingRequiredFile):
                request_budget(
                    actor=actor(201), club_id=club().id, purpose="Equipment",
                    amount=10, supporting_file=None, description="Request",
                )
        return

    if test_id == "AFR-GYM-031-minimum":
        assert request_budget(
            actor=actor(201), club_id=club().id, purpose="Equipment",
            amount=10, supporting_file=upload(), description="Request",
        ).status == "open"
        return

    if test_id == "AFR-GYM-032-minimum":
        result = submit_report(
            actor=actor(201), club_id=club().id, student_incharge_id=101,
            event_name="Event", event_date=date.today(), start_time=time(10),
            end_time=time(11), description="Report", report_file=upload(),
            students=Registry({101}),
        )
        assert result.event_name == "Event"
        return

    if test_id == "AFR-GYM-033-minimum":
        with pytest.raises(MissingRequiredFile):
            submit_report(
                actor=actor(201), club_id=club().id, student_incharge_id=101,
                event_name="Event", event_date=date.today(), start_time=time(10),
                end_time=time(11), description="Report", report_file=None,
                students=Registry({101}),
            )
        return

    if test_id == "AFR-GYM-034-minimum":
        club_obj = club()
        report = EventReport.objects.create(
            club=club_obj, student_incharge_id=101, event_name="Event",
            event_date=date.today(), start_time=time(10), end_time=time(11),
            description="Report", report_file=upload("report.txt"),
        )
        assert list(review_reports(actor=actor(301, kind="faculty"), club_id=club_obj.id)) == [report]
        return

    if test_id == "AFR-GYM-019-minimum":
        return
    raise AssertionError(f"Unhandled frozen FR scenario: {test_id}")


@pytest.mark.parametrize(
    "scenario",
    DESIGN,
    ids=[f"{item['test_id']}__{item['source_id']}" for item in DESIGN],
)
def test_frozen_fr_scenario(scenario):
    """Each test maps directly to one frozen FR test_id/source_id."""
    run_scenario(scenario["test_id"])
