from django.contrib import admin
from django.utils.html import format_html

from .models import SubmissionReviewQueue, StatusDistributionMetrics


# ===================================================================
#   SUBMISSION REVIEW QUEUE ADMIN
# ===================================================================
@admin.register(SubmissionReviewQueue)
class SubmissionReviewQueueAdmin(admin.ModelAdmin):
    list_display = (
        "submission_user",
        "department",
        "deadline_title",
        "review_status",
        "reviewer",
        "created_at",
    )

    list_filter = (
        "review_status",
        "department",
        "reviewer",
        "created_at",
    )

    search_fields = (
        "submission_status__user__username",
        "submission_status__user__first_name",
        "submission_status__user__last_name",
        "submission_status__deadline_setting__title",
    )

    autocomplete_fields = ("submission_status", "reviewer")

    readonly_fields = ("created_at", "department")

    ordering = ("-created_at",)

    # ----------------------------------------------------------------
    # Helper display methods
    # ----------------------------------------------------------------
    def submission_user(self, obj):
        return f"{obj.submission_status.user.get_full_name()} ({obj.submission_status.user.username})"
    submission_user.short_description = "User"

    def deadline_title(self, obj):
        return obj.submission_status.deadline_setting.title
    deadline_title.short_description = "Deadline"

    # ----------------------------------------------------------------
    # Admin Actions
    # ----------------------------------------------------------------
    actions = [
        "action_mark_in_review",
        "action_mark_approved",
        "action_mark_needs_revision",
        "action_mark_completed",
    ]

    def action_mark_in_review(self, request, queryset):
        count = 0
        for entry in queryset:
            entry.mark_as_in_review(request.user)
            count += 1
        self.message_user(request, f"{count} submission(s) marked as 'In Review'.")
    action_mark_in_review.short_description = "Mark as In Review"

    def action_mark_approved(self, request, queryset):
        count = 0
        for entry in queryset:
            entry.mark_as_approved(request.user)
            count += 1
        self.message_user(request, f"{count} submission(s) approved.")
    action_mark_approved.short_description = "Approve Submission"

    def action_mark_needs_revision(self, request, queryset):
        count = 0
        for entry in queryset:
            entry.mark_needs_revision(request.user)
            count += 1
        self.message_user(request, f"{count} submission(s) marked as Needs Revision.")
    action_mark_needs_revision.short_description = "Mark as Needs Revision"

    def action_mark_completed(self, request, queryset):
        count = 0
        for entry in queryset:
            entry.mark_as_completed()
            count += 1
        self.message_user(request, f"{count} submission(s) marked as Completed.")
    action_mark_completed.short_description = "Mark as Completed"


# ===================================================================
#   STATUS DISTRIBUTION METRICS ADMIN
# ===================================================================
@admin.register(StatusDistributionMetrics)
class StatusDistributionMetricsAdmin(admin.ModelAdmin):
    list_display = (
        "deadline_title",
        "department",
        "total_workers",
        "approved_count",
        "approved_percentage",
        "needs_revision_count",
        "pending_count",
        "in_progress_count",
        "late_count",
        "late_overdue_count",
        "last_updated",
    )

    list_filter = (
        "department",
        "deadline_setting__deadline_date",
        "last_updated",
    )

    search_fields = (
        "deadline_setting__title",
        "department__name",
    )

    readonly_fields = [
        "deadline_setting",
        "department",
        "total_workers",
        "approved_count",
        "approved_percentage",
        "needs_revision_count",
        "pending_count",
        "in_progress_count",
        "late_count",
        "late_overdue_count",
        "last_updated",
    ]

    ordering = ("-last_updated",)

    def deadline_title(self, obj):
        return obj.deadline_setting.title
    deadline_title.short_description = "Deadline"
