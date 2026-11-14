from django.db import transaction

from modules.gymkhana.models import Club, ClubLeadershipDesignation
from modules.gymkhana.services.adapters import StudentRegistry, student_registry
from modules.gymkhana.services.common import require_club_head, require_student


@transaction.atomic
def change_leadership(
    *,
    actor,
    club_id: int,
    coordinator_id: int,
    co_coordinator_id: int,
    students: StudentRegistry = student_registry,
) -> Club:
    # Spec: UC-GYM-008 preconditions, BR-GYM-010
    club = Club.objects.select_for_update().get(pk=club_id)
    require_club_head(club, actor)
    # Spec: UC-GYM-008 main flow step 2, BR-GYM-001, AFR-GYM-008
    require_student(coordinator_id, students)
    require_student(co_coordinator_id, students)
    # Spec: UC-GYM-008 main flow steps 3-6, AFR-GYM-009, BR-GYM-016
    ClubLeadershipDesignation.objects.filter(
        club=club, is_active=True
    ).update(is_active=False)
    ClubLeadershipDesignation.objects.bulk_create(
        [
            ClubLeadershipDesignation(
                club=club,
                student_id=coordinator_id,
                role=ClubLeadershipDesignation.Role.COORDINATOR,
            ),
            ClubLeadershipDesignation(
                club=club,
                student_id=co_coordinator_id,
                role=ClubLeadershipDesignation.Role.CO_COORDINATOR,
            ),
        ]
    )
    club.coordinator_id = coordinator_id
    club.co_coordinator_id = co_coordinator_id
    club.save(update_fields=["coordinator_id", "co_coordinator_id", "updated_at"])
    return club
