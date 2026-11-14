from dataclasses import dataclass
from typing import Iterable, Protocol


class StudentRegistry(Protocol):
    def is_valid_student(self, student_id: int) -> bool: ...

    def groups_for_student(self, student_id: int) -> set[tuple[int, str]]: ...

    def students_in_groups(self, groups: set[tuple[int, str]]) -> set[int]: ...


class FacultyRegistry(Protocol):
    def is_valid_faculty(self, faculty_id: int) -> bool: ...


class NotificationService(Protocol):
    def notify(self, *, recipients: Iterable[int], event: str, payload: dict) -> None: ...


@dataclass(frozen=True)
class DefaultStudentRegistry:
    def is_valid_student(self, student_id: int) -> bool:
        return isinstance(student_id, int) and student_id > 0

    def groups_for_student(self, student_id: int) -> set[tuple[int, str]]:
        return set()

    def students_in_groups(self, groups: set[tuple[int, str]]) -> set[int]:
        return set()


@dataclass(frozen=True)
class DefaultFacultyRegistry:
    def is_valid_faculty(self, faculty_id: int) -> bool:
        return isinstance(faculty_id, int) and faculty_id > 0


@dataclass(frozen=True)
class DefaultNotificationService:
    def notify(self, *, recipients: Iterable[int], event: str, payload: dict) -> None:
        return None


student_registry: StudentRegistry = DefaultStudentRegistry()
faculty_registry: FacultyRegistry = DefaultFacultyRegistry()
notification_service: NotificationService = DefaultNotificationService()
