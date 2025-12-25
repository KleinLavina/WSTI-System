from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Q
from accounts.forms import OrgAssignmentForm
    
from .models import (
    User,
    Team,
    OrgAssignment,
    WorkCycle,
    WorkAssignment,
    WorkItem,
    WorkItemAttachment,
    WorkItemMessage,
)

# ============================================================
# USER ADMIN
# ============================================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("username",)

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
        ("Work Information", {
            "fields": (
                "position_title",
                "login_role",
            )
        }),
    )


# ============================================================
# ORGANIZATIONAL STRUCTURE
# ============================================================

class OrgAssignmentInline(admin.StackedInline):
    """
    One resolved organizational path per user.
    """
    model = OrgAssignment
    extra = 0
    max_num = 1
    autocomplete_fields = ("division", "section", "service", "unit")


@admin.register(OrgAssignment)
class OrgAssignmentAdmin(admin.ModelAdmin):
    form = OrgAssignmentForm
    list_display = (
        "user",
        "division",
        "section",
        "service",
        "unit",
    )

    list_filter = (
        "division",
        "section",
        "service",
        "unit",
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
    )

    autocomplete_fields = (
        "user",
        "division",
        "section",
        "service",
        "unit",
    )


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "team_type",
        "parent",
        "created_at",
    )

    list_filter = (
        "team_type",
    )

    search_fields = (
        "name",
    )

    autocomplete_fields = (
        "parent",
    )

    ordering = (
        "team_type",
        "name",
    )


# ============================================================
# PLANNING (WHAT & WHEN)
# ============================================================

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
    )

    search_fields = (
        "title",
    )

    autocomplete_fields = (
        "created_by",
    )

    date_hierarchy = "due_at"


@admin.register(WorkAssignment)
class WorkAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "workcycle",
        "assigned_user",
        "assigned_team",
        "assigned_at",
    )

    list_filter = (
        "assigned_at",
    )

    autocomplete_fields = (
        "workcycle",
        "assigned_user",
        "assigned_team",
    )


# ============================================================
# EXECUTION (WORK ITEMS)
# ============================================================

class WorkItemAttachmentInline(admin.TabularInline):
    model = WorkItemAttachment
    extra = 0
    readonly_fields = ("uploaded_at",)
    autocomplete_fields = ("folder", "uploaded_by")


class WorkItemMessageInline(admin.TabularInline):
    model = WorkItemMessage
    extra = 0
    readonly_fields = ("created_at",)
    autocomplete_fields = ("sender",)


@admin.register(WorkItem)
class WorkItemAdmin(admin.ModelAdmin):
    list_display = (
        "workcycle",
        "owner",
        "status",
        "review_decision",
        "is_active",
        "created_at",
    )

    list_filter = (
        "status",
        "review_decision",
        "is_active",
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

    inlines = (
        WorkItemAttachmentInline,
        WorkItemMessageInline,
    )


@admin.register(WorkItemAttachment)
class WorkItemAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "work_item",
        "attachment_type",
        "uploaded_by",
        "uploaded_at",
    )

    list_filter = (
        "attachment_type",
    )

    autocomplete_fields = (
        "work_item",
        "folder",
        "uploaded_by",
    )


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
    )

    autocomplete_fields = (
        "work_item",
        "sender",
    )
