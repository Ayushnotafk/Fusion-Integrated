from datetime import date, time
from typing import Iterable

from django.db.models import Q

from modules.gymkhana.models import (
    Club,
    ClubEvent,
    ClubLeadershipDesignation,
    ClubSession,
    PollTargetGroup,
)
from modules.gymkhana.services.adapters import (
    FacultyRegistry,
    NotificationService,
    StudentRegistry,
    faculty_registry,
)
from modules.gymkhana.services.exceptions import (
    BookingConflict,
    InvalidAssignment,
    InvalidCategory,
    InvalidTimeRange,
    UnauthorizedClubOperation,
    VenueUnavailable,
)


def _actor_id(actor) -> int:
    value = getattr(actor, "user_id", actor if isinstance(actor, int) else None)
    if not isinstance(value, int) or value <= 0:
        raise UnauthorizedClubOperation("An authenticated actor is required.")
    return value


def require_student_admin(actor) -> int:
    # Spec: UC-GYM-001, UC-GYM-011
    actor_id = _actor_id(actor)
    role = getattr(actor, "active_role", None)
    permissions = getattr(actor, "permissions", ())
    if role not in {"student_admin", "student-admin"} and (
        "gymkhana.club.admin" not in permissions
    ):
        raise UnauthorizedClubOperation("Student Admin authorization is required.")
    return actor_id


def require_student(student_id: int, registry: StudentRegistry) -> int:
    # Spec: BR-GYM-001
    if not registry.is_valid_student(student_id):
        raise InvalidAssignment(f"Invalid student assignment: {student_id}.")
    return student_id


def require_student_actor(actor, registry: StudentRegistry) -> int:
    # Spec: UC-GYM-004, UC-GYM-007 preconditions
    if getattr(actor, "kind", None) != "student":
        raise InvalidAssignment("A student identity is required.")
    return require_student(getattr(actor, "user_id", None), registry)


def require_faculty(faculty_id: int, registry: FacultyRegistry) -> int:
    # Spec: BR-GYM-002
    if not registry.is_valid_faculty(faculty_id):
        raise InvalidAssignment(f"Invalid faculty assignment: {faculty_id}.")
    return faculty_id


def require_category(category: str) -> str:
    # Spec: BR-GYM-003
    if category not in Club.Category.values:
        raise InvalidCategory("Category must be Technical, Sports, or Cultural.")
    return category


def require_club_head(club: Club, actor) -> int:
    # Spec: BR-GYM-010
    actor_id = _actor_id(actor)
    if actor_id not in {club.coordinator_id, club.co_coordinator_id}:
        raise UnauthorizedClubOperation("Actor is not a Club Head for this club.")
    return actor_id


def require_confirmed_club(club: Club) -> Club:
    # Spec: BR-GYM-004, BR-GYM-007
    if club.status != Club.Status.CONFIRMED:
        raise UnauthorizedClubOperation("The club is not confirmed.")
    return club


def require_open_club(club: Club) -> Club:
    # Spec: BR-GYM-004
    if club.status != Club.Status.OPEN:
        raise UnauthorizedClubOperation("The club is not open.")
    return club


def require_configured_venue(venue) -> None:
    # Spec: BR-GYM-020
    if not venue.is_configured:
        raise VenueUnavailable("The venue is not configured.")


def require_time_range(start: time, end: time) -> None:
    # Spec: BR-GYM-005
    if start >= end:
        raise InvalidTimeRange("Start time must precede end time.")


def require_no_overlap(
    *,
    venue_id: int,
    booking_date: date,
    start: time,
    end: time,
) -> None:
    # Spec: BR-GYM-006
    overlaps = Q(start_time__lt=end) & Q(end_time__gt=start)
    if ClubSession.objects.filter(
        venue_id=venue_id, booking_date=booking_date
    ).filter(overlaps).exists() or ClubEvent.objects.filter(
        venue_id=venue_id, booking_date=booking_date
    ).filter(overlaps).exists():
        raise BookingConflict("The venue is already booked for this time.")


def notify(
    service: NotificationService,
    recipients: Iterable[int],
    event: str,
    payload: dict,
) -> None:
    service.notify(recipients=recipients, event=event, payload=payload)


def target_recipients(
    *,
    poll_id: int,
    student_registry: StudentRegistry,
) -> set[int]:
    # Spec: BR-GYM-013
    groups = set(
        PollTargetGroup.objects.filter(poll_id=poll_id).values_list("batch", "branch")
    )
    if not groups:
        raise InvalidAssignment("At least one target group is required.")
    # Spec: BR-GYM-013
    return student_registry.students_in_groups(groups)


def assigned_designation(club: Club, actor) -> ClubLeadershipDesignation:
    # Spec: BR-GYM-010, BR-GYM-016
    actor_id = require_club_head(club, actor)
    designation = ClubLeadershipDesignation.objects.filter(
        club=club, student_id=actor_id, is_active=True
    ).first()
    if designation is None:
        raise UnauthorizedClubOperation("Actor has no current Club Head designation.")
    return designation


def require_assigned_faculty(
    club: Club,
    actor,
    registry: FacultyRegistry = faculty_registry,
) -> int:
    # Spec: BR-GYM-021, UC-GYM-012 preconditions
    faculty_id = getattr(actor, "user_id", actor if isinstance(actor, int) else None)
    if faculty_id != club.faculty_councillor_id:
        raise UnauthorizedClubOperation("Faculty user is not assigned to this club.")
    require_faculty(faculty_id, registry)
    return faculty_id
