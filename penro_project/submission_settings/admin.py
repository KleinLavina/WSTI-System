from django.contrib import admin
from .models import (
    DeadlineSubmissionSetting,
    SubmissionStatus,
    DeadlineReminder,
    Notification,
)


# ---------------------------------------------------------------------
# DEADLINE SUBMISSION SETTING ADMIN
# ---------------------------------------------------------------------
@admin.register(DeadlineSubmissionSetting)
class DeadlineSubmissionSettingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "department",
        "start_date",
        "deadline_date",
        "created_at",
    )
    list_filter = ("department", "start_date", "deadline_date")
    search_fields = ("title", "department__name")
    ordering = ("deadline_date",)
    autocomplete_fields = ("department",)


# ---------------------------------------------------------------------
# SUBMISSION STATUS ADMIN
# ---------------------------------------------------------------------
@admin.register(SubmissionStatus)
class SubmissionStatusAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "deadline_setting",
        "status",
        "is_submitted",
        "submitted_at",
        "created_at",
    )
    list_filter = (
        "status",
        "is_submitted",
        "deadline_setting__department",
        "deadline_setting",
        "user",
    )
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "deadline_setting__title",
    )
    autocomplete_fields = ("deadline_setting", "user")
    readonly_fields = ("submitted_at", "created_at")
    ordering = ("-created_at",)

    actions = ["mark_as_submitted", "mark_as_approved", "mark_as_needs_revision"]

    # MARK AS SUBMITTED
    def mark_as_submitted(self, request, queryset):
        count = 0
        for obj in queryset:
            if not obj.is_submitted:
                obj.mark_submitted()
                count += 1
        self.message_user(request, f"{count} submission(s) marked as submitted.")

    mark_as_submitted.short_description = "Mark selected as Submitted"

    # MARK AS APPROVED
    def mark_as_approved(self, request, queryset):
        count = 0
        for obj in queryset:
            obj.mark_approved()
            count += 1
        self.message_user(request, f"{count} submission(s) approved.")

    mark_as_approved.short_description = "Approve selected submissions"

    # MARK AS NEEDS REVISION
    def mark_as_needs_revision(self, request, queryset):
        count = 0
        for obj in queryset:
            obj.mark_needs_revision()
            count += 1
        self.message_user(request, f"{count} submission(s) set to Needs Revision.")

    mark_as_needs_revision.short_description = "Mark selected as Needs Revision"


# ---------------------------------------------------------------------
# DEADLINE REMINDER ADMIN
# ---------------------------------------------------------------------
@admin.register(DeadlineReminder)
class DeadlineReminderAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "deadline_setting",
        "reminder_date",
        "is_sent",
        "created_at",
    )
    list_filter = (
        "is_sent",
        "reminder_date",
        "deadline_setting__department",
        "deadline_setting",
        "user",
    )
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "deadline_setting__title",
    )
    autocomplete_fields = ("deadline_setting", "user")
    readonly_fields = ("created_at",)
    ordering = ("reminder_date",)


# ---------------------------------------------------------------------
# NOTIFICATION ADMIN
# ---------------------------------------------------------------------
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__username", "title", "message")
    ordering = ("-created_at",)   # 🔥 Recommended improvement
