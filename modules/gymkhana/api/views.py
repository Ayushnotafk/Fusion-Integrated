from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import _envelope
from modules.gymkhana.api.permissions import (
    AssignedFacultyPermission,
    ClubHeadPermission,
    StudentAdminPermission,
    StudentPermission,
    permission_stack,
)
from modules.gymkhana.api.serializers import (
    ApplyMembershipSerializer,
    BudgetRequestSerializer,
    ClubEventSerializer,
    ClubLeadershipDesignationSerializer,
    ClubSerializer,
    ClubSessionSerializer,
    CreateBudgetRequestSerializer,
    CreateClubSerializer,
    CreateEventReportSerializer,
    CreatePollSerializer,
    EventBookingSerializer,
    EventReportSerializer,
    LeadershipChangeSerializer,
    MembershipApplicationSerializer,
    MembershipApprovalSerializer,
    PollSerializer,
    PollVoteSerializer,
    VoteSerializer,
    BookingSerializer,
)
from modules.gymkhana.models import (
    Club,
    ClubEvent,
    ClubSession,
    EventReport,
    MembershipApplication,
    Poll,
    PollVote,
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
    list_confirmed_clubs,
    list_pending_memberships,
    request_budget,
    review_reports,
    show_poll,
    submit_report,
    vote_poll,
)
from modules.gymkhana.services.adapters import student_registry
from modules.gymkhana.services.exceptions import GymkhanaServiceError


def actor(request):
    return getattr(request, "principal", None)


class GymkhanaAPIView(APIView):
    def handle_exception(self, exc):
        if isinstance(exc, GymkhanaServiceError):
            return _envelope(
                "gymkhana_error",
                str(exc),
                [],
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if isinstance(exc, ObjectDoesNotExist):
            return _envelope("not_found", "The requested resource was not found.", [], 404)
        return super().handle_exception(exc)


class CreateClubView(GymkhanaAPIView):
    permission_classes = permission_stack(StudentAdminPermission)

    def post(self, request):
        # Spec: UC-GYM-001
        payload = CreateClubSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return Response(
            ClubSerializer(
                create_club(actor=actor(request), **payload.validated_data)
            ).data,
            status=status.HTTP_201_CREATED,
        )


class ApproveClubView(GymkhanaAPIView):
    permission_classes = permission_stack(StudentAdminPermission)

    def post(self, request, club_id):
        # Spec: UC-GYM-011
        club = approve_club(actor=actor(request), club_id=club_id)
        return Response(ClubSerializer(club).data)


class BookSessionView(GymkhanaAPIView):
    permission_classes = permission_stack(ClubHeadPermission)
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, club_id):
        # Spec: UC-GYM-002
        payload = BookingSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        session = book_session(
            actor=actor(request),
            club_id=club_id,
            **payload.validated_data,
        )
        return Response(ClubSessionSerializer(session).data, status=201)


class BookEventView(GymkhanaAPIView):
    permission_classes = permission_stack(ClubHeadPermission)
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, club_id):
        # Spec: UC-GYM-003
        payload = EventBookingSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        event = book_event(actor=actor(request), club_id=club_id, **payload.validated_data)
        return Response(ClubEventSerializer(event).data, status=201)


class ConfirmedClubListView(GymkhanaAPIView):
    permission_classes = permission_stack(StudentPermission)

    def get(self, request):
        # Spec: UC-GYM-004 step 1
        clubs = list_confirmed_clubs()
        return Response({"results": ClubSerializer(clubs, many=True).data})


class ApplyMembershipView(GymkhanaAPIView):
    permission_classes = permission_stack(StudentPermission)

    def post(self, request, club_id):
        # Spec: UC-GYM-004
        payload = ApplyMembershipSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        application = apply_membership(
            actor=actor(request),
            club_id=club_id,
            students=self.student_registry,
            **payload.validated_data,
        )
        return Response(MembershipApplicationSerializer(application).data, status=201)


class PendingMembershipListView(GymkhanaAPIView):
    permission_classes = permission_stack(ClubHeadPermission)

    def get(self, request, club_id):
        # Spec: UC-GYM-005 step 1
        rows = list_pending_memberships(actor=actor(request), club_id=club_id)
        return Response({"results": MembershipApplicationSerializer(rows, many=True).data})


class ApproveMembershipView(GymkhanaAPIView):
    permission_classes = permission_stack(ClubHeadPermission)

    def post(self, request, club_id):
        # Spec: UC-GYM-005
        payload = MembershipApprovalSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        results = approve_memberships(
            actor=actor(request),
            club_id=club_id,
            **payload.validated_data,
        )
        return Response({"results": results})


class CreatePollView(GymkhanaAPIView):
    permission_classes = permission_stack(ClubHeadPermission)

    def post(self, request, club_id):
        # Spec: UC-GYM-006
        payload = CreatePollSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        poll = create_poll(actor=actor(request), club_id=club_id, **payload.validated_data)
        return Response(PollSerializer(poll).data, status=201)


class PollDetailView(GymkhanaAPIView):
    permission_classes = permission_stack(StudentPermission)

    def get(self, request, poll_id):
        # Spec: UC-GYM-007 step 1
        poll = show_poll(
            actor=actor(request),
            poll_id=poll_id,
            students=self.student_registry,
        )
        return Response(PollSerializer(poll).data)


class VotePollView(GymkhanaAPIView):
    permission_classes = permission_stack(StudentPermission)

    def post(self, request, poll_id):
        # Spec: UC-GYM-007
        payload = VoteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        vote = vote_poll(
            actor=actor(request),
            poll_id=poll_id,
            students=self.student_registry,
            **payload.validated_data,
        )
        return Response(PollVoteSerializer(vote).data, status=201)


class ChangeLeadershipView(GymkhanaAPIView):
    permission_classes = permission_stack(ClubHeadPermission)

    def post(self, request, club_id):
        # Spec: UC-GYM-008
        payload = LeadershipChangeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        club = change_leadership(actor=actor(request), club_id=club_id, **payload.validated_data)
        return Response(ClubSerializer(club).data)


class RequestBudgetView(GymkhanaAPIView):
    permission_classes = permission_stack(ClubHeadPermission)
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, club_id):
        # Spec: UC-GYM-009
        payload = CreateBudgetRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        budget = request_budget(actor=actor(request), club_id=club_id, **payload.validated_data)
        return Response(BudgetRequestSerializer(budget).data, status=201)


class SubmitReportView(GymkhanaAPIView):
    permission_classes = permission_stack(ClubHeadPermission)
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, club_id):
        # Spec: UC-GYM-010
        payload = CreateEventReportSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        report = submit_report(actor=actor(request), club_id=club_id, **payload.validated_data)
        return Response(EventReportSerializer(report).data, status=201)


class EventReportListView(GymkhanaAPIView):
    permission_classes = permission_stack(AssignedFacultyPermission)

    def get(self, request, club_id):
        # Spec: UC-GYM-012 steps 1-4
        reports = review_reports(actor=actor(request), club_id=club_id)
        return Response({"results": EventReportSerializer(reports, many=True).data})


class EventReportDetailView(GymkhanaAPIView):
    permission_classes = permission_stack(AssignedFacultyPermission)

    def get(self, request, club_id, report_id):
        # Spec: UC-GYM-012 steps 3-4
        reports = review_reports(actor=actor(request), club_id=club_id)
        report = reports.get(pk=report_id)
        return Response(EventReportSerializer(report).data)


GymkhanaAPIView.student_registry = student_registry
