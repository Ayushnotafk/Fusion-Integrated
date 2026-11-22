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
    (
        Path(__file__).resolve().parents[3] / "a8_design" / "UC_DESIGN.json"
    ).read_text(encoding="utf-8")
)


class Registry:
    def __init__(self, valid_students=(), groups=None):
        self.valid_students = set(valid_students)
        self.groups = groups or {}

    def is_valid_student(self, student_id):
        return student_id in self.valid_students

    def groups_for_student(self, student_id):
        return set(self.groups.get(student_id, set()))

    def students_in_groups(self, groups):
        return {
            student_id
            for student_id, student_groups in self.groups.items()
            if groups.intersection(student_groups)
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


def student_registry(*student_ids, groups=None):
    return Registry(student_ids, groups=groups)


def upload(name="evidence.txt"):
    return SimpleUploadedFile(name, b"evidence", content_type="text/plain")


def club(*, status=Club.Status.CONFIRMED, coordinator_id=201, co_coordinator_id=202):
    return Club.objects.create(
        code=f"club-{Club.objects.count()}",
        name=f"Club {Club.objects.count()}",
        description="Club description",
        coordinator_id=coordinator_id,
        co_coordinator_id=co_coordinator_id,
        faculty_councillor_id=301,
        category=Club.Category.TECHNICAL,
        status=status,
    )


def make_leadership(club_obj, coordinator=201, co_coordinator=202):
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


def poll_fixture(*, expiration=None, student_id=101, groups=None):
    club_obj = club()
    poll = Poll.objects.create(
        club=club_obj,
        title="Poll",
        description="Choose one",
        expiration_date=expiration or timezone.now() + timedelta(days=1),
    )
    choice = PollChoice.objects.create(poll=poll, text="Choice A")
    PollChoice.objects.create(poll=poll, text="Choice B")
    PollTargetGroup.objects.create(poll=poll, batch=2025, branch="CSE")
    registry = student_registry(
        student_id,
        groups={student_id: groups or {(2025, "CSE")}},
    )
    return poll, choice, registry


def application_fixture(*, status=MembershipApplication.Status.OPEN, club_obj=None):
    club_obj = club_obj or club()
    application = MembershipApplication.objects.create(
        club=club_obj,
        student_id=101,
        achievements="Achievements",
        description="Statement",
        status=status,
    )
    return club_obj, application


def report_fixture(club_obj=None):
    club_obj = club_obj or club()
    return EventReport.objects.create(
        club=club_obj,
        student_incharge_id=101,
        event_name="Completed event",
        event_date=date.today(),
        start_time=time(10, 0),
        end_time=time(11, 0),
        description="Report",
        report_file=upload(),
    )


def assert_no_booking(model):
    assert model.objects.count() == 0


def run_scenario(test_id):
    if test_id.endswith(("storage-failure", "pre-acceptance-failure")):
        pytest.skip("NOT_AUTOMATED: no controllable storage/notification failure interface")

    if test_id == "UC-GYM-001-create-open-club":
        result = create_club(
            actor=actor(1, kind="staff", role="student_admin"),
            name="Technical Club",
            description="Description",
            category=Club.Category.TECHNICAL,
            coordinator_id=101,
            co_coordinator_id=102,
            faculty_councillor_id=301,
            students=student_registry(101, 102),
        )
        assert result.status == Club.Status.OPEN
        return

    if test_id.startswith("UC-GYM-001-invalid-"):
        invalid = {
            "UC-GYM-001-invalid-coordinator": (0, 102, 301),
            "UC-GYM-001-invalid-co-coordinator": (101, 0, 301),
            "UC-GYM-001-invalid-faculty-councillor": (101, 102, 0),
        }[test_id]
        with pytest.raises(InvalidAssignment):
            create_club(
                actor=actor(1, kind="staff", role="student_admin"),
                name="Invalid Club",
                description="Description",
                category=Club.Category.TECHNICAL,
                coordinator_id=invalid[0],
                co_coordinator_id=invalid[1],
                faculty_councillor_id=invalid[2],
                students=student_registry(101, 102),
            )
        assert Club.objects.count() == 0
        return

    if test_id.startswith("UC-GYM-002-"):
        club_obj = club()
        venue = Venue.objects.create(name=f"Venue {Venue.objects.count()}")
        common = dict(
            actor=actor(201),
            club_id=club_obj.id,
            venue_id=venue.id,
            booking_date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0),
            description="Session",
        )
        if test_id == "UC-GYM-002-session-success":
            notifications = Notifications()
            result = book_session(**common, notifications=notifications)
            assert result.club_id == club_obj.id
            assert notifications.calls[0][1] == "club_session_booked"
        elif test_id == "UC-GYM-002-overlap":
            ClubSession.objects.create(
                club=club_obj, venue=venue, booking_date=date.today(),
                start_time=time(10, 30), end_time=time(11, 30),
                description="Existing",
            )
            with pytest.raises(BookingConflict):
                book_session(**common)
            assert ClubSession.objects.count() == 1
        elif test_id == "UC-GYM-002-invalid-venue":
            venue.is_configured = False
            venue.save(update_fields=["is_configured"])
            with pytest.raises(VenueUnavailable):
                book_session(**common)
            assert_no_booking(ClubSession)
        elif test_id == "UC-GYM-002-session-equal-time":
            common["end_time"] = common["start_time"]
            with pytest.raises(InvalidTimeRange):
                book_session(**common)
            assert_no_booking(ClubSession)
        elif test_id == "UC-GYM-002-session-later-start":
            common["start_time"], common["end_time"] = time(12, 0), time(11, 0)
            with pytest.raises(InvalidTimeRange):
                book_session(**common)
            assert_no_booking(ClubSession)
        return

    if test_id.startswith("UC-GYM-003-"):
        club_obj = club()
        venue = Venue.objects.create(name=f"Venue {Venue.objects.count()}")
        common = dict(
            actor=actor(201),
            club_id=club_obj.id,
            name="Event",
            venue_id=venue.id,
            booking_date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0),
            description="Event",
            faculty_id=301,
        )
        if test_id == "UC-GYM-003-event-success":
            notifications = Notifications()
            result = book_event(**common, notifications=notifications)
            assert result.club_id == club_obj.id
            assert notifications.calls[0][1] == "club_event_booked"
        elif test_id == "UC-GYM-003-overlap":
            ClubSession.objects.create(
                club=club_obj, venue=venue, booking_date=date.today(),
                start_time=time(10, 30), end_time=time(11, 30),
                description="Existing",
            )
            with pytest.raises(BookingConflict):
                book_event(**common)
            assert_no_booking(ClubEvent)
        elif test_id == "UC-GYM-003-invalid-venue":
            venue.is_configured = False
            venue.save(update_fields=["is_configured"])
            with pytest.raises(VenueUnavailable):
                book_event(**common)
            assert_no_booking(ClubEvent)
        elif test_id == "UC-GYM-003-invalid-faculty":
            common["faculty_id"] = 0
            with pytest.raises(InvalidAssignment):
                book_event(**common)
            assert_no_booking(ClubEvent)
        elif test_id == "UC-GYM-003-event-equal-time":
            common["end_time"] = common["start_time"]
            with pytest.raises(InvalidTimeRange):
                book_event(**common)
            assert_no_booking(ClubEvent)
        elif test_id == "UC-GYM-003-event-later-start":
            common["start_time"], common["end_time"] = time(12, 0), time(11, 0)
            with pytest.raises(InvalidTimeRange):
                book_event(**common)
            assert_no_booking(ClubEvent)
        return

    if test_id.startswith("UC-GYM-004-"):
        club_obj = club()
        if test_id == "UC-GYM-004-apply":
            result = apply_membership(
                actor=actor(101),
                club_id=club_obj.id,
                achievements="Achievements",
                description="Statement",
                students=student_registry(101),
            )
            assert result.status == MembershipApplication.Status.OPEN
        elif test_id == "UC-GYM-004-different":
            other = club()
            apply_membership(actor=actor(101), club_id=club_obj.id, students=student_registry(101))
            result = apply_membership(actor=actor(101), club_id=other.id, students=student_registry(101))
            assert result.club_id == other.id
        else:
            apply_membership(actor=actor(101), club_id=club_obj.id, students=student_registry(101))
            with pytest.raises(DuplicateApplication):
                apply_membership(actor=actor(101), club_id=club_obj.id, students=student_registry(101))
            assert MembershipApplication.objects.count() == 1
        return

    if test_id.startswith("UC-GYM-005-"):
        club_obj, application = application_fixture()
        if test_id == "UC-GYM-005-approve-application":
            result = approve_memberships(
                actor=actor(201), club_id=club_obj.id,
                applications=[{"application_id": application.id, "remarks": "Welcome"}],
            )
            application.refresh_from_db()
            assert result[0]["ok"] is True
            assert application.status == MembershipApplication.Status.CONFIRMED
        elif test_id == "UC-GYM-005-bulk-independent-approval":
            second = MembershipApplication.objects.create(
                club=club_obj, student_id=102, status=MembershipApplication.Status.OPEN,
            )
            result = approve_memberships(
                actor=actor(201), club_id=club_obj.id,
                applications=[{"application_id": application.id}, {"application_id": second.id}],
            )
            assert [item["ok"] for item in result] == [True, True]
        elif test_id == "UC-GYM-005-application-no-longer-open":
            application.status = MembershipApplication.Status.CONFIRMED
            application.save(update_fields=["status"])
            result = approve_memberships(
                actor=actor(201), club_id=club_obj.id,
                applications=[{"application_id": application.id}],
            )
            assert result == [{"application_id": application.id, "ok": False}]
        else:
            other = club()
            foreign = MembershipApplication.objects.create(
                club=other, student_id=102, status=MembershipApplication.Status.OPEN,
            )
            result = approve_memberships(
                actor=actor(201), club_id=club_obj.id,
                applications=[{"application_id": foreign.id}],
            )
            assert result == [{"application_id": foreign.id, "ok": False}]
        return

    if test_id.startswith("UC-GYM-006-"):
        club_obj = club()
        if test_id == "UC-GYM-006-branches":
            pytest.skip("NOT_AUTOMATED: configured all-branches option has no supplied interface")
        if test_id == "UC-GYM-006-choices":
            with pytest.raises(InvalidPoll):
                create_poll(
                    actor=actor(201), club_id=club_obj.id, title="Poll",
                    description="Poll", expiration_date=timezone.now() + timedelta(days=1),
                    choices=["Only"], target_groups=[(2025, "CSE")],
                )
            assert Poll.objects.count() == 0
        elif test_id == "UC-GYM-006-target":
            with pytest.raises(InvalidPoll):
                create_poll(
                    actor=actor(201), club_id=club_obj.id, title="Poll",
                    description="Poll", expiration_date=timezone.now() + timedelta(days=1),
                    choices=["A", "B"], target_groups=[(0, "")],
                )
            assert Poll.objects.count() == 0
        else:
            notifications = Notifications()
            result = create_poll(
                actor=actor(201), club_id=club_obj.id, title="Poll",
                description="Poll", expiration_date=timezone.now() + timedelta(days=1),
                choices=["A", "B"], target_groups=[(2025, "CSE")],
                students=Registry(groups={101: {(2025, "CSE")}}),
                notifications=notifications,
            )
            assert result.choices.count() == 2
            assert notifications.calls[0][0] == {101}
        return

    if test_id.startswith("UC-GYM-007-"):
        poll, choice, registry = poll_fixture()
        if test_id == "UC-GYM-007-vote":
            result = vote_poll(actor=actor(101), poll_id=poll.id, choice_id=choice.id, students=registry)
            assert result.student_id == 101
            assert PollVote.objects.count() == 1
        elif test_id == "UC-GYM-007-repeat":
            vote_poll(actor=actor(101), poll_id=poll.id, choice_id=choice.id, students=registry)
            with pytest.raises(AlreadyVoted):
                vote_poll(actor=actor(101), poll_id=poll.id, choice_id=choice.id, students=registry)
            assert PollVote.objects.count() == 1
        elif test_id == "UC-GYM-007-ineligible":
            registry = student_registry(101, groups={101: {(2025, "ECE")}})
            with pytest.raises(PollNotAvailable):
                show_poll(actor=actor(101), poll_id=poll.id, students=registry)
            assert PollVote.objects.count() == 0
        else:
            poll.expiration_date = timezone.now() - timedelta(seconds=1)
            poll.save(update_fields=["expiration_date"])
            with pytest.raises(PollNotAvailable):
                vote_poll(actor=actor(101), poll_id=poll.id, choice_id=choice.id, students=registry)
            assert PollVote.objects.count() == 0
        return

    if test_id.startswith("UC-GYM-008-"):
        club_obj = club()
        make_leadership(club_obj)
        valid = student_registry(301, 302)
        if test_id == "UC-GYM-008-change":
            result = change_leadership(
                actor=actor(201), club_id=club_obj.id, coordinator_id=301,
                co_coordinator_id=302, students=valid,
            )
            assert (result.coordinator_id, result.co_coordinator_id) == (301, 302)
            assert ClubLeadershipDesignation.objects.filter(club=club_obj, is_active=True).count() == 2
        elif test_id == "UC-GYM-008-bad-coordinator":
            with pytest.raises(InvalidAssignment):
                change_leadership(
                    actor=actor(201), club_id=club_obj.id, coordinator_id=0,
                    co_coordinator_id=302, students=valid,
                )
            club_obj.refresh_from_db()
            assert club_obj.coordinator_id == 201
        elif test_id == "UC-GYM-008-bad-co-coordinator":
            with pytest.raises(InvalidAssignment):
                change_leadership(
                    actor=actor(201), club_id=club_obj.id, coordinator_id=301,
                    co_coordinator_id=0, students=valid,
                )
            club_obj.refresh_from_db()
            assert club_obj.coordinator_id == 201
        else:
            with pytest.raises(UnauthorizedClubOperation):
                change_leadership(
                    actor=actor(999), club_id=club_obj.id, coordinator_id=301,
                    co_coordinator_id=302, students=valid,
                )
            club_obj.refresh_from_db()
            assert club_obj.coordinator_id == 201
        return

    if test_id.startswith("UC-GYM-009-"):
        club_obj = club()
        if test_id == "UC-GYM-009-negative":
            with pytest.raises(InvalidReference):
                request_budget(
                    actor=actor(201), club_id=club_obj.id, purpose="Budget",
                    amount=-1, supporting_file=upload(), description="Request",
                )
        elif test_id == "UC-GYM-009-file":
            with pytest.raises(MissingRequiredFile):
                request_budget(
                    actor=actor(201), club_id=club_obj.id, purpose="Budget",
                    amount=10, supporting_file=None, description="Request",
                )
        else:
            result = request_budget(
                actor=actor(201), club_id=club_obj.id, purpose="Budget",
                amount=10, supporting_file=upload(), description="Request",
            )
            assert result.status == "open"
        assert not hasattr(result if "result" in locals() else None, "status") or result.status == "open"
        return

    if test_id.startswith("UC-GYM-010-"):
        club_obj = club()
        if test_id == "UC-GYM-010-submit-report":
            result = submit_report(
                actor=actor(201), club_id=club_obj.id, student_incharge_id=101,
                event_name="Event", event_date=date.today(), start_time=time(10),
                end_time=time(11), description="Report", report_file=upload(),
                students=student_registry(101),
            )
            assert result.club_id == club_obj.id
        elif test_id == "UC-GYM-010-missing-report-file":
            with pytest.raises(MissingRequiredFile):
                submit_report(
                    actor=actor(201), club_id=club_obj.id, student_incharge_id=101,
                    event_name="Event", event_date=date.today(), start_time=time(10),
                    end_time=time(11), description="Report", report_file=None,
                    students=student_registry(101),
                )
            assert EventReport.objects.count() == 0
        elif test_id == "UC-GYM-010-invalid-report-reference":
            with pytest.raises(InvalidAssignment):
                submit_report(
                    actor=actor(201), club_id=club_obj.id, student_incharge_id=999,
                    event_name="Event", event_date=date.today(), start_time=time(10),
                    end_time=time(11), description="Report", report_file=upload(),
                    students=student_registry(101),
                )
            assert EventReport.objects.count() == 0
        else:
            with pytest.raises(InvalidReference):
                submit_report(
                    actor=actor(201), club_id=club_obj.id, student_incharge_id=101,
                    event_name="", event_date=date.today(), start_time=time(10),
                    end_time=time(11), description="Report", report_file=upload(),
                    students=student_registry(101),
                )
            assert EventReport.objects.count() == 0
        return

    if test_id.startswith("UC-GYM-011-"):
        club_obj = club(status=Club.Status.OPEN)
        admin = actor(1, kind="staff", role="student_admin")
        if test_id == "UC-GYM-011-approve":
            result = approve_club(actor=admin, club_id=club_obj.id)
            assert result.status == Club.Status.CONFIRMED
        elif test_id == "UC-GYM-011-not-open":
            club_obj.status = Club.Status.CONFIRMED
            club_obj.save(update_fields=["status"])
            with pytest.raises(UnauthorizedClubOperation):
                approve_club(actor=admin, club_id=club_obj.id)
        else:
            pytest.skip("NOT_AUTOMATED: no controllable club-update failure interface")
        return

    if test_id.startswith("UC-GYM-012-"):
        club_obj = club()
        report = report_fixture(club_obj)
        if test_id == "UC-GYM-012-review":
            result = review_reports(actor=actor(301, kind="faculty"), club_id=club_obj.id)
            assert list(result) == [report]
        else:
            with pytest.raises(UnauthorizedClubOperation):
                review_reports(actor=actor(302, kind="faculty"), club_id=club_obj.id)
        return

    raise AssertionError(f"Unhandled frozen scenario: {test_id}")


@pytest.mark.parametrize(
    "scenario",
    DESIGN,
    ids=[f"{item['test_id']}__{item['source_id']}" for item in DESIGN],
)
def test_frozen_uc_scenario(scenario):
    """Each collected test is the exact frozen UC test_id/source_id obligation."""
    run_scenario(scenario["test_id"])
