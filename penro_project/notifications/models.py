from django.db import models
from django.conf import settings
from django.utils import timezone

from accounts.models import WorkItem, WorkCycle


class Notification(models.Model):
    """
    A derived, user-facing notification.
    Notifications are NOT the source of truth — they reflect
    events happening in WorkItem, WorkCycle, etc.
    """

    # =====================================================
    # CATEGORY (matches your signal files 1:1)
    # =====================================================
    class Category(models.TextChoices):
        REMINDER = "reminder", "Reminder"
        STATUS = "status", "Status"
        REVIEW = "review", "Review"
        ASSIGNMENT = "assignment", "Assignment"
        MESSAGE = "message", "Message"
        SYSTEM = "system", "System"

    # =====================================================
    # SEVERITY / PRIORITY (UI + sorting)
    # =====================================================
    class Priority(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        DANGER = "danger", "Danger"

    # =====================================================
    # CORE RELATIONSHIPS
    # =====================================================
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        help_text="User who receives this notification"
    )

    # =====================================================
    # CLASSIFICATION
    # =====================================================
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        db_index=True
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.INFO,
        db_index=True
    )

    # =====================================================
    # CONTENT
    # =====================================================
    title = models.CharField(
        max_length=200,
        help_text="Short headline shown in notification list"
    )

    message = models.TextField(
        help_text="Detailed message shown when expanded"
    )

    # =====================================================
    # OPTIONAL CONTEXT (VERY IMPORTANT FOR GROUPING & LINKS)
    # =====================================================
    work_item = models.ForeignKey(
        WorkItem,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )

    workcycle = models.ForeignKey(
        WorkCycle,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )

    # Optional: link to any page (fallback)
    action_url = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional URL the notification should link to"
    )

    # =====================================================
    # STATE
    # =====================================================
    is_read = models.BooleanField(
        default=False,
        db_index=True
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )

    # =====================================================
    # DJANGO META
    # =====================================================
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["category"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["recipient", "category", "is_read"]),
        ]

    # =====================================================
    # STRING REPRESENTATION
    # =====================================================
    def __str__(self):
        return (
            f"{self.recipient} | "
            f"{self.category.upper()} | "
            f"{self.title}"
        )

    # =====================================================
    # INSTANCE HELPERS
    # =====================================================
    def mark_as_read(self):
        """Safely mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    # =====================================================
    # BULK HELPERS (IMPORTANT FOR UX)
    # =====================================================
    @classmethod
    def mark_all_as_read(cls, user, category=None):
        """
        Mark all unread notifications (optionally by category)
        as read for a user.
        """
        qs = cls.objects.filter(recipient=user, is_read=False)
        if category:
            qs = qs.filter(category=category)

        return qs.update(
            is_read=True,
            read_at=timezone.now()
        )
