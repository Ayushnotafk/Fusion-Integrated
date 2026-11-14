# Gymkhana implementation decisions and traceability

This document is the DELIVERABLE 5 audit for the synchronized Gymkhana
specification. Service functions are authoritative for business behavior.
Serializers perform only transport parsing and views perform only request
dispatch, response serialization, and exception mapping.

## 1. Decisions for ambiguous or silent specification points

| Ambiguity | Spec reference | Choice made | Implementation |
|---|---|---|---|
| Intended student recipients for session/event notifications are not defined. | AFR-GYM-013, AFR-GYM-015; UC-GYM-002/003 | Initiate notification through the adapter with an empty recipient set; do not invent recipient selection. | `book_session()` and `book_event()` in `services/uc_002_book_session.py` and `services/uc_003_book_event.py` |
| Faculty context applicability for an event is not defined. | AFR-GYM-014; UC-GYM-003; BR-GYM-002 | Treat the supplied faculty ID as the context and validate it through `FacultyRegistry`. | `book_event()` and `require_faculty()` |
| Whether touching time slots overlap is unspecified. | AFR-GYM-012; BR-GYM-006 | End time equal to another start time is adjacent, not overlapping; overlap uses strict `<`/`>`. | `require_no_overlap()` in `services/common.py` |
| Outcomes when use-case preconditions are unmet are unspecified. | UC-GYM-001..012 | Reject the operation before mutation and preserve state. | `require_*()` helpers and each UC service |
| Storage/notification failure injection and observable response are unspecified. | UC-GYM-001/002/003/011; BW-GYM-03 | Let the database/adapter exception propagate through `transaction.atomic`; no success is returned and no artificial failure contract is added. | All `@transaction.atomic` UC services |
| Concrete configured venue values are unspecified. | BR-GYM-020 | Use the explicit `Venue.is_configured` flag; no venue catalogue is invented. | `require_configured_venue()` |
| Poll expiry boundary is unspecified. | BR-GYM-014; UC-GYM-006/007 | A poll is unavailable when `expiration_date <= timezone.now()`. | `show_poll()` and `vote_poll()` |
| “All branches” configuration is unspecified. | BR-GYM-013; UC-GYM-006 | Require explicit `(batch, branch)` target groups; do not expand an all-branches sentinel. | `CreatePollSerializer` and `create_poll()` |
| Concrete invalid target-group values are unspecified. | UC-GYM-006; BR-GYM-013 | Require at least one target and validate positive batch/non-empty branch; registry data remains adapter-owned. | `create_poll()` |
| Whether a confirmed prior membership application counts as a duplicate is unresolved. | BR-GYM-009; AFR-GYM-018; AMB-006 | Reject any existing same-student/same-club application in the service, but do not add a database unique constraint. | `apply_membership()`; `services/membership.py` |
| Required event-report references are not enumerated. | UC-GYM-010; AMB-012 | Require the explicit report fields represented by the model: club, student incharge, event name, date/time, description, and report file. | `submit_report()` |
| “Required data” for club creation is not enumerated. | CFR-GYM-001; UC-GYM-001; AMB-013 | Require only the explicit model/service inputs; no extra required-data set is imposed. | `create_club()` and `CreateClubSerializer` |
| Error codes, messages, and response format are unspecified. | AMB-014 | Use the platform envelope with HTTP 422 for service-domain errors: `{"error":{"code":"gymkhana_error","message":"...","details":[],"request_id":"..."}}`. | `GymkhanaAPIView.handle_exception()` |
| Student Admin representation differs between the specification and shared auth principal. | UC-GYM-001/011; AMB-015 | Accept explicit `active_role` of `student_admin`/`student-admin` or `gymkhana.club.admin`. | `require_student_admin()` |
| Concrete student/faculty registry contents are unspecified. | BR-GYM-001/002; AMB-007 | Default adapters accept positive IDs only; deployments can provide authoritative registry adapters. | `services/adapters.py` |
| Whether an event must be linked to a previously recorded event is unspecified. | UC-GYM-010 precondition | Do not invent an event lookup; require only the submitted report references and file. | `submit_report()` |
| Behavior when the councillor has no reports is unspecified. | UC-GYM-012 | Return an empty list; do not invent a not-found or state transition. | `review_reports()` |

## 2. Final traceability

### Consolidated functional requirements (CFR)

| ID | Implementation |
|---|---|
| CFR-GYM-001 | `create_club()` in `services/uc_001_create_club.py`; `Club` in `models/clubs.py` |
| CFR-GYM-002 | `change_leadership()` in `services/uc_008_change_leadership.py`; `ClubLeadershipDesignation` |
| CFR-GYM-003 | `book_session()`/`book_event()`; `require_time_range()`/`require_no_overlap()` |
| CFR-GYM-004 | `apply_membership()`/`approve_memberships()` in UC-004/005 services |
| CFR-GYM-005 | `create_poll()`/`vote_poll()` in UC-006/007 services; poll models |
| CFR-GYM-006 | `request_budget()` in `services/uc_009_request_budget.py`; `BudgetRequest` |
| CFR-GYM-007 | `submit_report()`/`review_reports()` in UC-010/012 services; `EventReport` |

### Atomic functional requirements (AFR)

| ID | Implementation |
|---|---|
| AFR-GYM-001 | `create_club()`; `Club` coordinator/co-coordinator/faculty fields |
| AFR-GYM-002 | `require_student()` in `services/common.py`; `create_club()` and `change_leadership()` |
| AFR-GYM-003 | `require_faculty()`; `create_club()` and `book_event()` |
| AFR-GYM-004 | `require_category()` and `Club.Category` |
| AFR-GYM-005 | `create_club()` sets `Club.Status.OPEN` |
| AFR-GYM-006 | `approve_club()` sets `Club.Status.CONFIRMED` |
| AFR-GYM-007 | `ClubLeadershipDesignation`; `create_club()` and `change_leadership()` |
| AFR-GYM-008 | `require_student()` in `change_leadership()` |
| AFR-GYM-009 | `change_leadership()` retires active designations and creates the replacements |
| AFR-GYM-010 | `book_session()` and `ClubSession` |
| AFR-GYM-011 | `require_time_range()` |
| AFR-GYM-012 | `require_no_overlap()` across `ClubSession` and `ClubEvent` |
| AFR-GYM-013 | Notification initiation in `book_session()` |
| AFR-GYM-014 | `book_event()` and `ClubEvent` |
| AFR-GYM-015 | Notification initiation in `book_event()` |
| AFR-GYM-016 | `apply_membership()` and `MembershipApplication` |
| AFR-GYM-017 | No cross-club duplicate check in `apply_membership()` |
| AFR-GYM-018 | Same-club duplicate check in `apply_membership()` |
| AFR-GYM-019 | `apply_membership()` sets status `open` |
| AFR-GYM-020 | `list_pending_memberships()` and `PendingMembershipListView` |
| AFR-GYM-021 | `approve_memberships()` and `remarks` field |
| AFR-GYM-022 | `approve_memberships()` transitions `open` to `confirmed` |
| AFR-GYM-023 | `create_poll()` and `Poll` |
| AFR-GYM-024 | `create_poll()` requires at least two choices |
| AFR-GYM-025 | `target_recipients()` and notification in `create_poll()` |
| AFR-GYM-026 | `show_poll()` validates active audience membership |
| AFR-GYM-027 | `vote_poll()` records one selected choice |
| AFR-GYM-028 | `PollVote` and `vote_poll()` |
| AFR-GYM-029 | `request_budget()` and `BudgetRequest` |
| AFR-GYM-030 | `request_budget()` validates amount/file |
| AFR-GYM-031 | `BudgetRequest.Status.OPEN` and `request_budget()` |
| AFR-GYM-032 | `submit_report()` and `EventReport` |
| AFR-GYM-033 | `submit_report()` requires `report_file` |
| AFR-GYM-034 | `review_reports()` and `AssignedFacultyPermission` |

### Use cases (UC)

| ID | Implementation |
|---|---|
| UC-GYM-001 | `create_club()`; `CreateClubView` |
| UC-GYM-002 | `book_session()`; `BookSessionView` |
| UC-GYM-003 | `book_event()`; `BookEventView` |
| UC-GYM-004 | `list_confirmed_clubs()` and `apply_membership()`; confirmed-club and membership endpoints |
| UC-GYM-005 | `list_pending_memberships()` and `approve_memberships()` |
| UC-GYM-006 | `create_poll()`; `CreatePollView` |
| UC-GYM-007 | `show_poll()` and `vote_poll()`; `PollDetailView`/`VotePollView` |
| UC-GYM-008 | `change_leadership()`; `ChangeLeadershipView` |
| UC-GYM-009 | `request_budget()`; `RequestBudgetView` |
| UC-GYM-010 | `submit_report()`; `SubmitReportView` |
| UC-GYM-011 | `approve_club()`; `ApproveClubView` |
| UC-GYM-012 | `review_reports()`; `EventReportListView`/`EventReportDetailView` |

### Business rules (BR)

| ID | Implementation |
|---|---|
| BR-GYM-001 | `require_student()`; UC-001, UC-008, UC-010 |
| BR-GYM-002 | `require_faculty()`; UC-001 and UC-003 |
| BR-GYM-003 | `require_category()`; UC-001 |
| BR-GYM-004 | `Club.Status`, `require_open_club()`, `require_confirmed_club()`, UC-001/011 |
| BR-GYM-005 | `require_time_range()` and model check constraints |
| BR-GYM-006 | `require_no_overlap()` |
| BR-GYM-007 | `require_confirmed_club()` in `apply_membership()` |
| BR-GYM-008 | Same-club-only duplicate query in `apply_membership()` |
| BR-GYM-009 | Service duplicate rejection in `apply_membership()`; intentionally no DB constraint |
| BR-GYM-010 | `require_club_head()` in services and `ClubHeadPermission` |
| BR-GYM-011 | `approve_memberships()` plus membership status constraint |
| BR-GYM-012 | `create_poll()` choice count |
| BR-GYM-013 | `PollTargetGroup`, `target_recipients()`, and poll audience checks |
| BR-GYM-014 | `show_poll()`/`vote_poll()` active and audience checks |
| BR-GYM-015 | `PollVote` unique constraint and `vote_poll()` duplicate check |
| BR-GYM-016 | `ClubLeadershipDesignation.is_active` and `change_leadership()` |
| BR-GYM-017 | `BudgetRequest` non-negative DB constraint and `request_budget()` |
| BR-GYM-018 | `request_budget()` required supporting file |
| BR-GYM-019 | `submit_report()` required report file |
| BR-GYM-020 | `Venue.is_configured` and `require_configured_venue()` |
| BR-GYM-021 | `require_assigned_faculty()` and `review_reports()` |

### Business workflows (BW)

| ID | Implementation |
|---|---|
| BW-GYM-01 | `apply_membership()` -> `MembershipApplication.OPEN` -> `approve_memberships()` -> `CONFIRMED` |
| BW-GYM-02 | `create_poll()` -> target groups/poll open -> `vote_poll()` -> `PollVote` |
| BW-GYM-03 | `create_club()` -> `OPEN` -> `approve_club()` -> `CONFIRMED` |

## 3. Self-audit

### Specification items not fully implemented

| Item | Status and reason |
|---|---|
| AFR-GYM-013 and AFR-GYM-015 notification delivery to the intended student recipients | Notification initiation is implemented, but recipient resolution is not. The specification does not define the recipient source; the default adapter intentionally receives an empty set. |
| AFR-GYM-025 notification delivery to poll target students | Target-group persistence and adapter call are implemented, but the default registry returns no concrete students because the shared registry contract/data is unspecified. |
| UC-GYM-010 precondition that the relevant event/activity has occurred | Not independently validated because no event-occurrence record or interface is specified. The service records the supplied report data and required file. |
| Poll tally mutation described by UC-GYM-007 | A `PollVote` record is created, which is the persisted tally source. No denormalized counter was added because no tally field or update mechanism is specified. |

### Behavior not directly justified by the specification

| Behavior | Location | Audit action |
|---|---|---|
| `Club.code` is retained and auto-derived from the name when omitted. | `Club`, `CreateClubSerializer`, `create_club()` | Flagged: the synchronized text does not define a code field. It remains for compatibility with the pre-existing model/API and is not used for a business decision. |
| `ClubLeadershipDesignation.Role.HEAD` and the `ClubCoordinatorAssignment` compatibility alias remain available. | `models/clubs.py`, `models/__init__.py` | Flagged: the accepted spec names coordinator and co-coordinator only. The alias/role is retained solely for existing infrastructure compatibility; service authorization uses the Club coordinator/co-coordinator IDs. |
| Positive-ID and max-length checks occur in serializers/default adapters. | API serializers and `services/adapters.py` | Accepted as transport/type parsing and adapter fallback behavior, not business-state validation. Authoritative student/faculty checks still occur in services. |
| `PollTargetGroup` and leadership partial uniqueness constraints prevent duplicate current rows. | Poll/club models | Accepted as data-integrity protection supporting the stated target/current-leadership concepts; they do not add a new workflow state or transition. |
| Service-domain failures use HTTP 422 and a platform envelope. | `GymkhanaAPIView.handle_exception()` | Flagged and documented above because the spec is silent on error format. |

### Business-rule enforcement location audit

No BR-GYM-001..021 is enforced only in a serializer or view. The service layer
contains the authoritative checks. Permissions call the same shared service
helpers for early authorization rejection, and serializers only parse types,
multipart files, and input shape.

| Rule group | Service authority |
|---|---|
| BR-GYM-001..004 | `services/common.py`, `uc_001_create_club.py`, `uc_008_change_leadership.py`, `uc_011_approve_club.py` |
| BR-GYM-005..006 | `require_time_range()` and `require_no_overlap()` |
| BR-GYM-007..011 | UC-004/005 services and `services/membership.py` |
| BR-GYM-012..016 | UC-006/007/008 services and poll/leadership models |
| BR-GYM-017..021 | UC-009/010/012 services, `require_configured_venue()`, and `require_assigned_faculty()` |
