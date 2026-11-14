class GymkhanaServiceError(Exception):
    """Base error for rejected Gymkhana service operations."""


class InvalidAssignment(GymkhanaServiceError):
    pass


class InvalidCategory(GymkhanaServiceError):
    pass


class InvalidState(GymkhanaServiceError):
    pass


class UnauthorizedClubOperation(GymkhanaServiceError):
    pass


class VenueUnavailable(GymkhanaServiceError):
    pass


class InvalidTimeRange(GymkhanaServiceError):
    pass


class BookingConflict(GymkhanaServiceError):
    pass


class DuplicateApplication(GymkhanaServiceError):
    pass


class InvalidPoll(GymkhanaServiceError):
    pass


class PollNotAvailable(GymkhanaServiceError):
    pass


class AlreadyVoted(GymkhanaServiceError):
    pass


class MissingRequiredFile(GymkhanaServiceError):
    pass


class InvalidReference(GymkhanaServiceError):
    pass
