from django.db import transaction

from modules.gymkhana.models import Club, ClubSession, Venue
from modules.gymkhana.services.adapters import (
    NotificationService as NotificationAdapter,
    notification_service,
)
from modules.gymkhana.services.common import (
    notify,
    require_club_head,
    require_confirmed_club,
    require_configured_venue,
    require_no_overlap,
    require_time_range,
)


@transaction.atomic
def book_session(
    *,
    actor,
    club_id: int,
    venue_id: int,
    booking_date,
    start_time,
    end_time,
    description: str,
    poster=None,
    notifications: NotificationAdapter = notification_service,
) -> ClubSession:
    # Spec: UC-GYM-002 preconditions, BR-GYM-010
    club = Club.objects.get(pk=club_id)
    require_club_head(club, actor)
    require_confirmed_club(club)
    venue = Venue.objects.get(pk=venue_id)
    # Spec: UC-GYM-002 main flow steps 2-5, BR-GYM-005, BR-GYM-006, BR-GYM-020
    require_configured_venue(venue)
    require_time_range(start_time, end_time)
    require_no_overlap(
        venue_id=venue.id,
        booking_date=booking_date,
        start=start_time,
        end=end_time,
    )
    session = ClubSession.objects.create(
        club=club,
        venue=venue,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        description=description,
        poster=poster,
    )
    # Spec: AFR-GYM-013, UC-GYM-002 main flow step 7
    notify(notifications, (), "club_session_booked", {"session_id": session.id})
    return session
