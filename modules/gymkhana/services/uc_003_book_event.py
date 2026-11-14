from django.db import transaction

from modules.gymkhana.models import Club, ClubEvent, Venue
from modules.gymkhana.services.adapters import (
    FacultyRegistry,
    NotificationService,
    faculty_registry,
    notification_service,
)
from modules.gymkhana.services.common import (
    notify,
    require_club_head,
    require_confirmed_club,
    require_configured_venue,
    require_faculty,
    require_no_overlap,
    require_time_range,
)


@transaction.atomic
def book_event(
    *,
    actor,
    club_id: int,
    name: str,
    venue_id: int,
    booking_date,
    start_time,
    end_time,
    description: str,
    faculty_id: int,
    poster=None,
    faculty: FacultyRegistry = faculty_registry,
    notifications: NotificationService = notification_service,
) -> ClubEvent:
    # Spec: UC-GYM-003 preconditions, BR-GYM-010
    club = Club.objects.get(pk=club_id)
    require_club_head(club, actor)
    require_confirmed_club(club)
    venue = Venue.objects.get(pk=venue_id)
    # Spec: UC-GYM-003 main flow steps 2-6, BR-GYM-002, BR-GYM-005, BR-GYM-006, BR-GYM-020
    require_faculty(faculty_id, faculty)
    require_configured_venue(venue)
    require_time_range(start_time, end_time)
    require_no_overlap(
        venue_id=venue.id,
        booking_date=booking_date,
        start=start_time,
        end=end_time,
    )
    event = ClubEvent.objects.create(
        club=club,
        name=name,
        venue=venue,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        description=description,
        poster=poster,
        faculty_id=faculty_id,
    )
    # Spec: AFR-GYM-015, UC-GYM-003 main flow step 8
    notify(notifications, (), "club_event_booked", {"event_id": event.id})
    return event
