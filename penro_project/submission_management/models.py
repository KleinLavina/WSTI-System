from django.db import models
from django.utils import timezone

from accounts.models import Department, User
from submission_settings.models import DeadlineSubmissionSetting, SubmissionStatus
# NOTE: SubmissionReviewQueue is defined below, so we import it locally inside refresh_metrics to avoid circular imports.


# ============================================================
#   SUBMISSION REVIEW QUEUE
# ============================================================
class SubmissionReviewQueue(models.Model):
    submission_status = models.OneToOneField(
        SubmissionStatus,
        on_delete=models.CASCADE,
        related_name="review_queue_entry"
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        editable=False
    )

    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    review_status = models.CharField(
        max_length=20,
        choices=[
            ("pending_review", "Pending Review"),
            ("approved", "Approved"),
            ("needs_revision", "Needs Revision"),
        ],
        default="pending_review"
    )

    reviewer_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.department = self.submission_status.deadline_setting.department
        super().save(*args, **kwargs)

    # ---------------------------------------------------
    # REVIEW ACTIONS
    # ---------------------------------------------------
    def mark_approved(self, reviewer=None):
        if reviewer:
            self.reviewer = reviewer

        self.review_status = "approved"
        self.save()

        # update submission status
        self.submission_status.status = "approved"
        self.submission_status.save()

    def mark_needs_revision(self, reviewer=None, notes=""):
        if reviewer:
            self.reviewer = reviewer
        if notes:
            self.reviewer_notes = notes

        # update submission status
        self.submission_status.status = "needs_revision"
        self.submission_status.save()

        # REMOVE THIS ENTRY FROM REVIEW QUEUE
        self.delete()


# ============================================================
#   STATUS DISTRIBUTION METRICS
# ============================================================
class StatusDistributionMetrics(models.Model):
    """
    Metrics per DeadlineSubmissionSetting:
    - total_workers: department.users.count()
    - approved_count / needs_revision_count → from SubmissionReviewQueue
    - other counts → from SubmissionStatus
    - approved_percentage → derived field
    """

    deadline_setting = models.OneToOneField(
        DeadlineSubmissionSetting,
        on_delete=models.CASCADE,
        related_name="status_metrics"
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="status_metrics"
    )

    # Metrics counters
    total_workers = models.IntegerField(default=0)

    # Review queue-based stats
    approved_count = models.IntegerField(default=0)
    needs_revision_count = models.IntegerField(default=0)

    # Submission status-based stats
    pending_count = models.IntegerField(default=0)
    in_progress_count = models.IntegerField(default=0)
    late_count = models.IntegerField(default=0)
    late_overdue_count = models.IntegerField(default=0)

    # Derived metric
    approved_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00
    )

    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Metrics: {self.deadline_setting.title} — {self.department.name}"

    # -------------------------------------------------------
    # RECALCULATE METRICS
    # -------------------------------------------------------
    def refresh_metrics(self):
        """
        Recompute:
        - Total workers (from department)
        - Counts from SubmissionReviewQueue
        - Counts from SubmissionStatus
        - Approved percentage
        """

        # 1) Total workers from the department assigned to the deadline
        self.total_workers = self.deadline_setting.department.users.count()

        # 2) Counts from SubmissionReviewQueue (import inside function avoids circular import)
        from submission_management.models import SubmissionReviewQueue

        review_qs = SubmissionReviewQueue.objects.filter(
            submission_status__deadline_setting=self.deadline_setting
        )

        self.approved_count = review_qs.filter(review_status="approved").count()
        self.needs_revision_count = review_qs.filter(review_status="needs_revision").count()

        # 3) Counts from SubmissionStatus
        submissions = SubmissionStatus.objects.filter(
            deadline_setting=self.deadline_setting
        )

        self.pending_count = submissions.filter(status="pending").count()
        self.in_progress_count = submissions.filter(status="in_progress").count()
        self.late_count = submissions.filter(status="late").count()
        self.late_overdue_count = submissions.filter(status="late_overdue").count()

        # 4) Derived metric
        if self.total_workers > 0:
            self.approved_percentage = (self.approved_count / self.total_workers) * 100
        else:
            self.approved_percentage = 0.0

        self.save()
