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
    submit_report,
    vote_poll,
)
from modules.gymkhana.services.exceptions import (
    AlreadyVoted,
    BookingConflict,
    DuplicateApplication,
    InvalidAssignment,
    InvalidCategory,
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
    (Path(__file__).resolve().parents[3] / "a8_design" / "BR_DESIGN.json").read_text(
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
        user_id=user_id,
        kind=kind,
        active_role=role,
        permissions=(),
    )


def upload():
    return SimpleUploadedFile("evidence.txt", b"evidence", content_type="text/plain")


def make_club(*, status=Club.Status.CONFIRMED):
    number = Club.objects.count()
    return Club.objects.create(
        code=f"br-club-{number}",
        name=f"BR Club {number}",
        description="Business rule club",
        coordinator_id=201,
        co_coordinator_id=202,
        faculty_councillor_id=301,
        category=Club.Category.TECHNICAL,
        status=status,
    )


def leadership(club_obj):
    ClubLeadershipDesignation.objects.bulk_create(
        [
            ClubLeadershipDesignation(
                club=club_obj,
                student_id=201,
                role=ClubLeadershipDesignation.Role.COORDINATOR,
            ),
            ClubLeadershipDesignation(
                club=club_obj,
                student_id=202,
                role=ClubLeadershipDesignation.Role.CO_COORDINATOR,
            ),
        ]
    )


def run_scenario(test_id):
    if test_id == "BR-GYM-001-invalid-coordinator":
        with pytest.raises(InvalidAssignment):
            create_club(
                actor=actor(1, kind="staff", role="student_admin"),
                name="Club", description="Description",
                category=Club.Category.TECHNICAL,
                coordinator_id=0, co_coordinator_id=102, faculty_councillor_id=301,
                students=Registry({102}),
            )
        return
    if test_id == "BR-GYM-001-invalid-co-coordinator":
        with pytest.raises(InvalidAssignment):
            create_club(
                actor=actor(1, kind="staff", role="student_admin"),
                name="Club", description="Description",
                category=Club.Category.TECHNICAL,
                coordinator_id=101, co_coordinator_id=0, faculty_councillor_id=301,
                students=Registry({101}),
            )
        return
    if test_id == "BR-GYM-001-invalid-replacement-leader":
        club_obj = make_club()
        leadership(club_obj)
        with pytest.raises(InvalidAssignment):
            change_leadership(
                actor=actor(201), club_id=club_obj.id,
                coordinator_id=0, co_coordinator_id=302, students=Registry({302}),
            )
        club_obj.refresh_from_db()
        assert club_obj.coordinator_id == 201
        return
    if test_id == "BR-GYM-002-invalid-faculty":
        with pytest.raises(InvalidAssignment):
            create_club(
                actor=actor(1, kind="staff", role="student_admin"),
                name="Club", description="Description",
                category=Club.Category.TECHNICAL,
                coordinator_id=101, co_coordinator_id=102, faculty_councillor_id=0,
                students=Registry({101, 102}),
            )
        return
    if test_id == "BR-GYM-003-allowed-categories":
        for category in Club.Category.values:
            result = create_club(
                actor=actor(1, kind="staff", role="student_admin"),
                name=f"Club {category}", description="Description",
                category=category, coordinator_id=101, co_coordinator_id=102,
                faculty_councillor_id=301, students=Registry({101, 102}),
            )
            assert result.category == category
        return
    if test_id == "BR-GYM-003-unsupported-category":
        with pytest.raises(InvalidCategory):
            create_club(
                actor=actor(1, kind="staff", role="student_admin"),
                name="Club", description="Description", category="Other",
                coordinator_id=101, co_coordinator_id=102, faculty_councillor_id=301,
                students=Registry({101, 102}),
            )
        return
    if test_id == "BR-GYM-004-creation-open-approval-confirmed":
        result = create_club(
            actor=actor(1, kind="staff", role="student_admin"),
            name="Lifecycle Club", description="Description",
            category=Club.Category.TECHNICAL, coordinator_id=101,
            co_coordinator_id=102, faculty_councillor_id=301,
            students=Registry({101, 102}),
        )
        assert result.status == Club.Status.OPEN
        result = approve_club(
            actor=actor(1, kind="staff", role="student_admin"), club_id=result.id
        )
        assert result.status == Club.Status.CONFIRMED
        return

    if test_id.startswith("BR-GYM-005-"):
        club_obj = make_club()
        venue = Venue.objects.create(name="BR Venue")
        common = dict(
            actor=actor(201), club_id=club_obj.id, venue_id=venue.id,
            booking_date=date.today(), description="Booking",
        )
        if test_id == "BR-GYM-005-start-before-end":
            result = book_session(
                **common, start_time=time(10), end_time=time(11)
            )
            assert result.start_time < result.end_time
        elif test_id == "BR-GYM-005-equal-times":
            with pytest.raises(InvalidTimeRange):
                book_session(
                    **common, start_time=time(10), end_time=time(10)
                )
        else:
            with pytest.raises(InvalidTimeRange):
                book_session(
                    **common, start_time=time(11), end_time=time(10)
                )
        return

    if test_id.startswith("BR-GYM-006-"):
        club_obj = make_club()
        venue = Venue.objects.create(name="Overlap Venue")
        if test_id == "BR-GYM-006-session-session-overlap":
            ClubSession.objects.create(
                club=club_obj, venue=venue, booking_date=date.today(),
                start_time=time(10), end_time=time(11), description="Existing",
            )
            with pytest.raises(BookingConflict):
                book_session(
                    actor=actor(201), club_id=club_obj.id, venue_id=venue.id,
                    booking_date=date.today(), start_time=time(10, 30),
                    end_time=time(11, 30), description="New",
                )
        elif test_id == "BR-GYM-006-event-event-overlap":
            ClubEvent.objects.create(
                club=club_obj, name="Existing", venue=venue,
                booking_date=date.today(), start_time=time(10), end_time=time(11),
                description="Existing", faculty_id=301,
            )
            with pytest.raises(BookingConflict):
                book_event(
                    actor=actor(201), club_id=club_obj.id, name="New",
                    venue_id=venue.id, booking_date=date.today(),
                    start_time=time(10, 30), end_time=time(11, 30),
                    description="New", faculty_id=301,
                )
        else:
            ClubSession.objects.create(
                club=club_obj, venue=venue, booking_date=date.today(),
                start_time=time(10), end_time=time(11), description="Existing",
            )
            with pytest.raises(BookingConflict):
                book_event(
                    actor=actor(201), club_id=club_obj.id, name="New",
                    venue_id=venue.id, booking_date=date.today(),
                    start_time=time(10, 30), end_time=time(11, 30),
                    description="New", faculty_id=301,
                )
        return

    if test_id.startswith("BR-GYM-007-"):
        club_obj = make_club(
            status=Club.Status.CONFIRMED
            if test_id.endswith("confirmed-club-required")
            else Club.Status.OPEN
        )
        if test_id.endswith("confirmed-club-required"):
            result = apply_membership(
                actor=actor(101), club_id=club_obj.id, students=Registry({101})
            )
            assert result.club_id == club_obj.id
        else:
            with pytest.raises(UnauthorizedClubOperation):
                apply_membership(
                    actor=actor(101), club_id=club_obj.id, students=Registry({101})
                )
        return

    if test_id == "BR-GYM-008-different-clubs-allowed":
        first, second = make_club(), make_club()
        apply_membership(actor=actor(101), club_id=first.id, students=Registry({101}))
        result = apply_membership(
            actor=actor(101), club_id=second.id, students=Registry({101})
        )
        assert result.club_id == second.id
        return
    if test_id == "BR-GYM-009-same-club-duplicate":
        club_obj = make_club()
        apply_membership(actor=actor(101), club_id=club_obj.id, students=Registry({101}))
        with pytest.raises(DuplicateApplication):
            apply_membership(
                actor=actor(101), club_id=club_obj.id, students=Registry({101})
            )
        assert MembershipApplication.objects.count() == 1
        return

    if test_id.startswith("BR-GYM-010-"):
        club_obj = make_club()
        operation = dict(
            actor=actor(201), club_id=club_obj.id, venue_id=Venue.objects.create(
                name="Auth Venue"
            ).id, booking_date=date.today(), start_time=time(10),
            end_time=time(11), description="Booking",
        )
        if test_id.endswith("applicable-coordinator-authorized"):
            assert book_session(**operation).club_id == club_obj.id
        else:
            operation["actor"] = actor(999)
            with pytest.raises(UnauthorizedClubOperation):
                book_session(**operation)
        return

    if test_id == "BR-GYM-011-open-to-confirmed":
        club_obj = make_club()
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
        assert application.remarks == "Approved"
        return

    if test_id.startswith("BR-GYM-012-"):
        club_obj = make_club()
        if test_id.endswith("two-choices"):
            poll = create_poll(
                actor=actor(201), club_id=club_obj.id, title="Poll",
                description="Poll", expiration_date=timezone.now() + timedelta(days=1),
                choices=["A", "B"], target_groups=[(2025, "CSE")],
            )
            assert poll.choices.count() == 2
        else:
            with pytest.raises(InvalidPoll):
                create_poll(
                    actor=actor(201), club_id=club_obj.id, title="Poll",
                    description="Poll", expiration_date=timezone.now() + timedelta(days=1),
                    choices=["A"], target_groups=[(2025, "CSE")],
                )
        return

    if test_id == "BR-GYM-013-selected-audience":
        club_obj = make_club()
        notifications = Notifications()
        create_poll(
            actor=actor(201), club_id=club_obj.id, title="Poll",
            description="Poll", expiration_date=timezone.now() + timedelta(days=1),
            choices=["A", "B"], target_groups=[(2025, "CSE")],
            students=Registry(groups={101: {(2025, "CSE")}, 102: {(2025, "ECE")}}),
            notifications=notifications,
        )
        assert notifications.calls[0][0] == {101}
        return
    if test_id == "BR-GYM-013-all-branches-where-supported":
        pytest.skip("NOT_AUTOMATED: no configured all-branches selection interface")

    if test_id.startswith("BR-GYM-014-"):
        club_obj = make_club()
        poll = Poll.objects.create(
            club=club_obj, title="Poll", description="Poll",
            expiration_date=timezone.now() + timedelta(days=1),
        )
        choice = PollChoice.objects.create(poll=poll, text="A")
        PollTargetGroup.objects.create(poll=poll, batch=2025, branch="CSE")
        if test_id.endswith("eligible-active-poll"):
            from modules.gymkhana.services import show_poll

            assert show_poll(
                actor=actor(101), poll_id=poll.id,
                students=Registry({101}, {101: {(2025, "CSE")}}),
            ).id == poll.id
        else:
            poll.expiration_date = timezone.now() - timedelta(seconds=1)
            poll.save(update_fields=["expiration_date"])
            with pytest.raises(PollNotAvailable):
                vote_poll(
                    actor=actor(101), poll_id=poll.id, choice_id=choice.id,
                    students=Registry({101}, {101: {(2025, "ECE")}}),
                )
        return

    if test_id.startswith("BR-GYM-015-"):
        club_obj = make_club()
        poll = Poll.objects.create(
            club=club_obj, title="Poll", description="Poll",
            expiration_date=timezone.now() + timedelta(days=1),
        )
        choice = PollChoice.objects.create(poll=poll, text="A")
        PollTargetGroup.objects.create(poll=poll, batch=2025, branch="CSE")
        registry = Registry({101}, {101: {(2025, "CSE")}})
        vote_poll(actor=actor(101), poll_id=poll.id, choice_id=choice.id, students=registry)
        if test_id.endswith("first-vote-allowed"):
            assert PollVote.objects.count() == 1
        else:
            with pytest.raises(AlreadyVoted):
                vote_poll(
                    actor=actor(101), poll_id=poll.id, choice_id=choice.id,
                    students=registry,
                )
        return

    if test_id == "BR-GYM-016-retire-superseded-leaders":
        club_obj = make_club()
        leadership(club_obj)
        change_leadership(
            actor=actor(201), club_id=club_obj.id,
            coordinator_id=301, co_coordinator_id=302, students=Registry({301, 302}),
        )
        assert ClubLeadershipDesignation.objects.filter(
            club=club_obj, is_active=True
        ).count() == 2
        assert not ClubLeadershipDesignation.objects.filter(
            club=club_obj, student_id__in=[201, 202], is_active=True
        ).exists()
        return

    if test_id.startswith("BR-GYM-017-"):
        club_obj = make_club()
        kwargs = dict(
            actor=actor(201), club_id=club_obj.id, purpose="Budget",
            supporting_file=upload(), description="Request",
        )
        if test_id.endswith("zero-or-positive"):
            result = request_budget(**kwargs, amount=0)
            assert result.amount == 0
        else:
            with pytest.raises(InvalidReference):
                request_budget(**kwargs, amount=-1)
        return

    if test_id.startswith("BR-GYM-018-"):
        club_obj = make_club()
        kwargs = dict(
            actor=actor(201), club_id=club_obj.id, purpose="Budget",
            amount=10, description="Request",
        )
        if test_id.endswith("file-present"):
            assert request_budget(**kwargs, supporting_file=upload()).status == "open"
        else:
            with pytest.raises(MissingRequiredFile):
                request_budget(**kwargs, supporting_file=None)
        return

    if test_id.startswith("BR-GYM-019-"):
        club_obj = make_club()
        kwargs = dict(
            actor=actor(201), club_id=club_obj.id, student_incharge_id=101,
            event_name="Event", event_date=date.today(), start_time=time(10),
            end_time=time(11), description="Report", students=Registry({101}),
        )
        if test_id.endswith("file-present"):
            assert submit_report(**kwargs, report_file=upload()).club_id == club_obj.id
        else:
            with pytest.raises(MissingRequiredFile):
                submit_report(**kwargs, report_file=None)
        return

    if test_id.startswith("BR-GYM-020-"):
        club_obj = make_club()
        venue = Venue.objects.create(
            name="Configured Venue", is_configured=not test_id.endswith("unconfigured-venue")
        )
        kwargs = dict(
            actor=actor(201), club_id=club_obj.id, venue_id=venue.id,
            booking_date=date.today(), start_time=time(10), end_time=time(11),
            description="Session",
        )
        if test_id == "BR-GYM-020-configured-venue":
            assert book_session(**kwargs).venue_id == venue.id
        else:
            with pytest.raises(VenueUnavailable):
                book_session(**kwargs)
        return

    if test_id.startswith("BR-GYM-021-"):
        club_obj = make_club()
        EventReport.objects.create(
            club=club_obj, student_incharge_id=101, event_name="Event",
            event_date=date.today(), start_time=time(10), end_time=time(11),
            description="Report", report_file=upload(),
        )
        faculty_id = 301 if test_id.endswith("assigned-councillor") else 302
        if faculty_id == 301:
            assert review_reports(actor=actor(faculty_id, kind="faculty"), club_id=club_obj.id).count() == 1
        else:
            with pytest.raises(UnauthorizedClubOperation):
                review_reports(actor=actor(faculty_id, kind="faculty"), club_id=club_obj.id)
        return

    raise AssertionError(f"Unhandled BR scenario: {test_id}")


@pytest.mark.parametrize(
    "scenario",
    DESIGN,
    ids=[f"{item['test_id']}__{item['source_id']}" for item in DESIGN],
)
def test_frozen_br_scenario(scenario):
    """Each test maps directly to one frozen BR test_id/source_id."""
    run_scenario(scenario["test_id"])
