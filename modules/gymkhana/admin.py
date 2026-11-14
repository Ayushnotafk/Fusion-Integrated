from django.contrib import admin

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


admin.site.register(
    [
        Club,
        ClubLeadershipDesignation,
        Venue,
        ClubSession,
        ClubEvent,
        MembershipApplication,
        Poll,
        PollChoice,
        PollTargetGroup,
        PollVote,
        BudgetRequest,
        EventReport,
    ]
)
