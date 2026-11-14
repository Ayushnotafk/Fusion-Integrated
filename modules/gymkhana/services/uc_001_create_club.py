from django.db import transaction

from modules.gymkhana.models import Club, ClubLeadershipDesignation
from modules.gymkhana.services.adapters import (
    FacultyRegistry,
    StudentRegistry,
    faculty_registry,
    student_registry,
)
from modules.gymkhana.services.common import (
    require_category,
    require_faculty,
    require_student,
    require_student_admin,
)


@transaction.atomic
def create_club(
    *,
    actor,
    name: str,
    description: str,
    category: str,
    coordinator_id: int,
    co_coordinator_id: int,
    faculty_councillor_id: int,
    code: str | None = None,
    students: StudentRegistry = student_registry,
    faculty: FacultyRegistry = faculty_registry,
) -> Club:
    # Spec: UC-GYM-001 preconditions
    require_student_admin(actor)
    # Spec: BR-GYM-003
    require_category(category)
    # Spec: BR-GYM-001
    require_student(coordinator_id, students)
    require_student(co_coordinator_id, students)
    # Spec: BR-GYM-002
    require_faculty(faculty_councillor_id, faculty)
    # Spec: UC-GYM-001 main flow steps 1-6, BW-GYM-03
    club = Club.objects.create(
        code=code or name.lower().replace(" ", "-"),
        name=name,
        description=description,
        coordinator_id=coordinator_id,
        co_coordinator_id=co_coordinator_id,
        faculty_councillor_id=faculty_councillor_id,
        category=category,
        status=Club.Status.OPEN,
    )
    # Spec: AFR-GYM-007, BR-GYM-016
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
    return club
