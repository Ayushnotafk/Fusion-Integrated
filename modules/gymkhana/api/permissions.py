from rest_framework.permissions import BasePermission

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.gymkhana.models import Club
from modules.gymkhana.services.common import (
    require_assigned_faculty,
    require_club_head,
    require_student_actor,
    require_student_admin,
)
from modules.gymkhana.services.adapters import faculty_registry
from modules.gymkhana.services.exceptions import GymkhanaServiceError


MODULE = HasModuleGrant("gymkhana")


def _club_from_request(request, view):
    club_id = view.kwargs.get("club_id") or request.data.get("club_id")
    if not club_id:
        return None
    try:
        return Club.objects.get(pk=club_id)
    except (Club.DoesNotExist, TypeError, ValueError):
        return None


class StudentAdminPermission(BasePermission):
    message = "Student Admin authorization is required."

    def has_permission(self, request, view):
        try:
            require_student_admin(getattr(request, "principal", None))
        except GymkhanaServiceError:
            return False
        return True


class ClubHeadPermission(BasePermission):
    message = "The actor is not a Club Head for this club."

    def has_permission(self, request, view):
        club = _club_from_request(request, view)
        if club is None:
            return False
        try:
            require_club_head(club, getattr(request, "principal", None))
        except GymkhanaServiceError:
            return False
        return True


class StudentPermission(BasePermission):
    message = "A student identity is required."

    def has_permission(self, request, view):
        principal = getattr(request, "principal", None)
        if getattr(principal, "kind", None) != "student":
            return False
        try:
            require_student_actor(principal, view.student_registry)
        except GymkhanaServiceError:
            return False
        return True


class AssignedFacultyPermission(BasePermission):
    message = "The faculty user is not assigned to this club."

    def has_permission(self, request, view):
        club = _club_from_request(request, view)
        principal = getattr(request, "principal", None)
        try:
            require_assigned_faculty(club, principal, faculty_registry)
        except GymkhanaServiceError:
            return False
        return True


def permission_stack(*permissions):
    return [MODULE, *permissions]
