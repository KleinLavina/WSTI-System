from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User,
    Team,
    TeamMembership,
    WorkCycle,
    WorkAssignment,
    WorkItem,
    WorkItemAttachment,
    WorkItemMessage,
)

# ============================================================
# USER
# ============================================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "position_title",
        "login_role",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "login_role",
        "is_active",
        "is_staff",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Work Info", {
            "fields": ("position_title", "login_role"),
        }),
    )


# ============================================================
# TEAM & MEMBERSHIP
# ============================================================

class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 1
    autocomplete_fields = ("user",)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)
    inlines = (TeamMembershipInline,)


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("team", "user", "role", "joined_at")
    list_filter = ("team", "role")
    search_fields = (
        "team__name",
        "user__username",
        "user__first_name",
        "user__last_name",
    )
    autocomplete_fields = ("team", "user")


# ============================================================
# WORK CYCLE
# ============================================================

class WorkAssignmentInline(admin.TabularInline):
    model = WorkAssignment
    extra = 0
    autocomplete_fields = ("assigned_user", "assigned_team")
    readonly_fields = ("assigned_at",)


@admin.register(WorkCycle)
class WorkCycleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "due_at",
        "is_active",
        "created_by",
        "created_at",
    )

    list_filter = (
        "is_active",
        "due_at",
    )

    search_fields = (
        "title",
        "description",
        "created_by__username",
    )

    autocomplete_fields = ("created_by",)

    inlines = (WorkAssignmentInline,)

    date_hierarchy = "due_at"


# ============================================================
# WORK ASSIGNMENT
# ============================================================

@admin.register(WorkAssignment)
class WorkAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "workcycle",
        "assigned_user",
        "assigned_team",
        "assigned_at",
    )

    list_filter = (
        "assigned_team",
        "assigned_at",
    )

    search_fields = (
        "workcycle__title",
        "assigned_user__username",
        "assigned_team__name",
    )

    autocomplete_fields = (
        "workcycle",
        "assigned_user",
        "assigned_team",
    )


# ============================================================
# WORK ITEM
# ============================================================

class WorkItemAttachmentInline(admin.TabularInline):
    model = WorkItemAttachment
    extra = 0
    readonly_fields = ("uploaded_at",)


class WorkItemMessageInline(admin.TabularInline):
    model = WorkItemMessage
    extra = 0
    readonly_fields = ("sender", "sender_role", "created_at")
    can_delete = False


@admin.register(WorkItem)
class WorkItemAdmin(admin.ModelAdmin):
    list_display = (
        "workcycle",
        "owner",
        "status",
        "review_decision",
        "is_active",
        "submitted_at",
        "created_at",
    )

    list_filter = (
        "status",
        "review_decision",
        "is_active",
        "inactive_reason",
    )

    search_fields = (
        "workcycle__title",
        "owner__username",
        "owner__first_name",
        "owner__last_name",
    )

    autocomplete_fields = (
        "workcycle",
        "owner",
    )

    readonly_fields = (
        "submitted_at",
        "inactive_at",
        "created_at",
    )

    inlines = (
        WorkItemAttachmentInline,
        WorkItemMessageInline,
    )

    ordering = ("-created_at",)


# ============================================================
# WORK ITEM ATTACHMENT
# ============================================================

@admin.register(WorkItemAttachment)
class WorkItemAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "work_item",
        "uploaded_by",
        "uploaded_at",
    )

    search_fields = (
        "work_item__workcycle__title",
        "uploaded_by__username",
    )

    autocomplete_fields = (
        "work_item",
        "uploaded_by",
    )


# ============================================================
# WORK ITEM MESSAGE
# ============================================================

@admin.register(WorkItemMessage)
class WorkItemMessageAdmin(admin.ModelAdmin):
    list_display = (
        "work_item",
        "sender",
        "sender_role",
        "created_at",
    )

    list_filter = (
        "sender_role",
        "created_at",
    )

    search_fields = (
        "work_item__workcycle__title",
        "sender__username",
        "message",
    )

    autocomplete_fields = (
        "work_item",
        "sender",
    )

    readonly_fields = ("created_at",)
