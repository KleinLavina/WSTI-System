from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from submission_settings.models import (
    DeadlineSubmissionSetting,
    SubmissionStatus
)

from submission_management.models import (
    StatusDistributionMetrics,
    SubmissionReviewQueue
)


# ===========================================================
# 1) CREATE METRICS WHEN DEADLINE IS CREATED
# ===========================================================
@receiver(post_save, sender=DeadlineSubmissionSetting)
def create_metrics_for_deadline(sender, instance, created, **kwargs):
    if not created:
        return

    metrics, _ = StatusDistributionMetrics.objects.get_or_create(
        deadline_setting=instance,
        defaults={"department": instance.department}
    )

    metrics.refresh_metrics()


# ===========================================================
# 2) REFRESH METRICS WHEN REVIEW QUEUE CHANGES
# ===========================================================
@receiver(post_save, sender=SubmissionReviewQueue)
@receiver(post_delete, sender=SubmissionReviewQueue)
def refresh_metrics_on_review_change(sender, instance, **kwargs):
    deadline = instance.submission_status.deadline_setting

    metrics, _ = StatusDistributionMetrics.objects.get_or_create(
        deadline_setting=deadline,
        defaults={"department": deadline.department}
    )

    metrics.refresh_metrics()


# ===========================================================
# 3) SYNC REVIEW QUEUE WITH SUBMISSION STATUS
# ===========================================================
@receiver(post_save, sender=SubmissionStatus)
def sync_review_queue(sender, instance, **kwargs):
    """
    Queue rule:
    - If status == 'complete' → ensure it exists in review queue
    - Else                 → remove from review queue
    """
    from submission_management.models import SubmissionReviewQueue

    # Must be included in review queue
    if instance.status == "complete":
        SubmissionReviewQueue.objects.get_or_create(
            submission_status=instance
        )
        return

    # If status changed away from 'complete', remove queue entry
    SubmissionReviewQueue.objects.filter(
        submission_status=instance
    ).delete()
