# notifications/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from accounts.models import WorkItem


class Notification(models.Model):
    TYPE_CHOICES = [
        ("chat", "Chat Message"),
        ("review", "Review Decision"),
        ("status", "Work Status"),
        ("reminder", "Deadline Reminder"),
        ("system", "System"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    notif_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        db_index=True
    )

    title = models.CharField(max_length=200)
    message = models.TextField()

    # Context
    work_item = models.ForeignKey(
        WorkItem,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )

    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["notif_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.recipient} | {self.notif_type} | {self.title}"
