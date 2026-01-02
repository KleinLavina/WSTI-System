from django.contrib import admin
from django.utils.html import format_html

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin configuration for system notifications
    (aligned with updated Notification model)
    """

    # =====================================================
    # LIST VIEW
    # =====================================================
    list_display = (
        "id",
        "recipient",
        "category",
        "priority",
        "colored_title",
        "is_read",
        "created_at",
    )

    list_filter = (
        "category",
        "priority",
        "is_read",
        "created_at",
    )

    search_fields = (
        "title",
        "message",
        "recipient__username",
        "recipient__first_name",
        "recipient__last_name",
    )

    ordering = ("-created_at",)
    list_per_page = 25

    # =====================================================
    # FIELDSETS (DETAIL VIEW)
    # =====================================================
    fieldsets = (
        ("Recipient", {
            "fields": ("recipient",),
        }),
        ("Classification", {
            "fields": ("category", "priority"),
        }),
        ("Content", {
            "fields": ("title", "message"),
        }),
        ("Context", {
            "fields": ("workcycle", "work_item", "action_url"),
        }),
        ("Status", {
            "fields": ("is_read", "read_at", "created_at"),
        }),
    )

    readonly_fields = (
        "created_at",
        "read_at",
    )

    # =====================================================
    # ACTIONS
    # =====================================================
    actions = (
        "mark_as_read",
        "mark_as_unread",
    )

    # =====================================================
    # CUSTOM DISPLAY HELPERS
    # =====================================================
    def colored_title(self, obj):
        """
        Color the title based on category for fast scanning.
        """
        color_map = {
            Notification.Category.REMINDER: "#f59e0b",    # orange
            Notification.Category.STATUS: "#16a34a",      # green
            Notification.Category.REVIEW: "#7c3aed",      # purple
            Notification.Category.ASSIGNMENT: "#2563eb",  # blue
            Notification.Category.MESSAGE: "#0ea5e9",     # sky
            Notification.Category.SYSTEM: "#6b7280",      # gray
        }

        color = color_map.get(obj.category, "#000000")

        return format_html(
            '<span style="color:{}; font-weight:600;">{}</span>',
            color,
            obj.title,
        )

    colored_title.short_description = "Title"

    # =====================================================
    # ADMIN ACTIONS
    # =====================================================
    @admin.action(description="Mark selected notifications as READ")
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description="Mark selected notifications as UNREAD")
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
