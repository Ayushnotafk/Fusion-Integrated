from rest_framework import serializers

from modules.gymkhana.models import (
    BudgetRequest,
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


class ClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = [
            "id", "code", "name", "description", "coordinator_id",
            "co_coordinator_id", "faculty_councillor_id", "category", "status",
        ]


class CreateClubSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    code = serializers.SlugField(max_length=60, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.ChoiceField(choices=Club.Category.choices)
    coordinator_id = serializers.IntegerField(min_value=1)
    co_coordinator_id = serializers.IntegerField(min_value=1)
    faculty_councillor_id = serializers.IntegerField(min_value=1)


class BookingSerializer(serializers.Serializer):
    venue_id = serializers.IntegerField(min_value=1)
    booking_date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    description = serializers.CharField()
    poster = serializers.FileField(required=False, allow_null=True)


class EventBookingSerializer(BookingSerializer):
    name = serializers.CharField(max_length=160)
    faculty_id = serializers.IntegerField(min_value=1)


class MembershipApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipApplication
        fields = [
            "id", "club", "student_id", "achievements", "description",
            "status", "remarks", "created_at", "updated_at",
        ]
        read_only_fields = fields


class ApplyMembershipSerializer(serializers.Serializer):
    achievements = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)


class MembershipApprovalItemSerializer(serializers.Serializer):
    application_id = serializers.IntegerField(min_value=1)
    remarks = serializers.CharField(required=False, allow_blank=True)


class MembershipApprovalSerializer(serializers.Serializer):
    applications = MembershipApprovalItemSerializer(many=True, allow_empty=False)


class LeadershipChangeSerializer(serializers.Serializer):
    coordinator_id = serializers.IntegerField(min_value=1)
    co_coordinator_id = serializers.IntegerField(min_value=1)


class PollChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollChoice
        fields = ["id", "text"]


class PollTargetGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollTargetGroup
        fields = ["id", "batch", "branch"]


class PollSerializer(serializers.ModelSerializer):
    choices = PollChoiceSerializer(many=True, read_only=True)
    target_groups = PollTargetGroupSerializer(many=True, read_only=True)

    class Meta:
        model = Poll
        fields = [
            "id", "club", "title", "description", "expiration_date",
            "choices", "target_groups", "created_at", "updated_at",
        ]


class CreatePollSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=160)
    description = serializers.CharField(required=False, allow_blank=True)
    expiration_date = serializers.DateTimeField()
    choices = serializers.ListField(
        child=serializers.CharField(max_length=240),
        allow_empty=False,
    )
    target_groups = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )

    def validate_target_groups(self, value):
        return [
            (item.get("batch"), item.get("branch"))
            for item in value
        ]


class VoteSerializer(serializers.Serializer):
    choice_id = serializers.IntegerField(min_value=1)


class BudgetRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetRequest
        fields = [
            "id", "club", "purpose", "amount", "supporting_file",
            "description", "status", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "club", "status", "created_at", "updated_at"]


class CreateBudgetRequestSerializer(serializers.Serializer):
    purpose = serializers.CharField(max_length=240)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    supporting_file = serializers.FileField()
    description = serializers.CharField(required=False, allow_blank=True)


class EventReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventReport
        fields = [
            "id", "club", "student_incharge_id", "event_name", "event_date",
            "start_time", "end_time", "description", "report_file",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class CreateEventReportSerializer(serializers.Serializer):
    student_incharge_id = serializers.IntegerField(min_value=1)
    event_name = serializers.CharField(max_length=160)
    event_date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    description = serializers.CharField()
    report_file = serializers.FileField()


class ClubLeadershipDesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubLeadershipDesignation
        fields = ["id", "student_id", "role", "is_active"]


class ClubSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubSession
        fields = [
            "id", "club", "venue", "booking_date", "start_time", "end_time",
            "description", "poster", "created_at", "updated_at",
        ]


class ClubEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubEvent
        fields = [
            "id", "club", "name", "venue", "booking_date", "start_time",
            "end_time", "description", "poster", "faculty_id",
            "created_at", "updated_at",
        ]


class PollVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollVote
        fields = ["id", "poll", "choice", "student_id", "created_at"]
