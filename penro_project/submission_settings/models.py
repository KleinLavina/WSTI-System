from django.utils import timezone
from django.db import models
from accounts.models import Department, User


class DeadlineSubmissionSetting(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="deadline_settings"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    start_date = models.DateField()
    deadline_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.department.name}"


class SubmissionStatus(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("late_overdue", "Late / Overdue"),
        ("late", "Late"),
        ("complete", "Complete"),

        # NEW statuses
        ("needs_revision", "Needs Revision"),
        ("approved", "Approved"),
    ]

    deadline_setting = models.ForeignKey(
        DeadlineSubmissionSetting,
        on_delete=models.CASCADE,
        related_name="submission_statuses"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="submission_statuses"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    is_submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)

    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("deadline_setting", "user")

    # -------------------------------------------------
    # MARK SUBMITTED
    # -------------------------------------------------
    def mark_submitted(self):
        from .models import DeadlineReminder, Notification
        from submission_management.models import SubmissionReviewQueue

        self.is_submitted = True
        self.submitted_at = timezone.now()

        deadline = self.deadline_setting.deadline_date

        if self.submitted_at.date() <= deadline:
            self.status = "complete"
        else:
            self.status = "late"

        self.save()

        # CANCEL FUTURE REMINDERS
        DeadlineReminder.objects.filter(
            deadline_setting=self.deadline_setting,
            user=self.user,
            is_sent=False
        ).update(is_sent=True)

        # CREATE REVIEW QUEUE ENTRY IF NOT EXISTS
        SubmissionReviewQueue.objects.get_or_create(
            submission_status=self,
            defaults={}
        )

        # SEND COMPLETION NOTIFICATION
        Notification.objects.create(
            user=self.user,
            submission_status=self,
            title="Submission Completed 🎉",
            message=f"Congratulations! You successfully submitted the report '{self.deadline_setting.title}'. Great job!"
        )


    # -------------------------------------------------
    # MARK NEEDS REVISION
    # -------------------------------------------------
    def mark_needs_revision(self, remarks=""):
        from .models import Notification

        self.status = "needs_revision"
        if remarks:
            self.remarks = remarks
        self.save()

        Notification.objects.create(
            user=self.user,
            submission_status=self,
            title="Submission Requires Revision",
            message=(
                f"Your submission for '{self.deadline_setting.title}' "
                f"needs revision. Please review the remarks and update your report."
            )   
        )

    # -------------------------------------------------
    # MARK APPROVED
    # -------------------------------------------------
    def mark_approved(self):
        from .models import Notification

        self.status = "approved"
        self.save()

        Notification.objects.create(
            user=self.user,
            submission_status=self,
            title="Submission Approved ✔️",
            message=(
                f"Good news! Your submission for '{self.deadline_setting.title}' "
                f"has been reviewed and approved."
            )
        )

    def __str__(self):
        return f"{self.user} - {self.status}"


class DeadlineReminder(models.Model):
    deadline_setting = models.ForeignKey(
        DeadlineSubmissionSetting,
        on_delete=models.CASCADE,
        related_name="reminders"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="deadline_reminders"
    )

    reminder_date = models.DateTimeField()
    is_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reminder for {self.user} - {self.deadline_setting.title}"


class Notification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    # Nullable because some notifications are not tied to a submission
    submission_status = models.ForeignKey(
        SubmissionStatus,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True, 
        blank=True
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username} - {self.title}"

