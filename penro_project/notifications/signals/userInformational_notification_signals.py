from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from notifications.models import Notification
from accounts.models import WorkItem, WorkCycle


# =====================================================
# WORK REVIEW RESULT (APPROVED / REVISION ACCEPTED)
# =====================================================
@receiver(post_save, sender=WorkItem)
def notify_user_review_result(sender, instance, created, **kwargs):
    if created:
        return

    # Fetch previous review decision safely
    previous_review = (
        WorkItem.objects
        .filter(pk=instance.pk)
        .values_list("review_decision", flat=True)
        .first()
    )

    # -----------------------------
    # WORK APPROVED (FIRST TIME)
    # -----------------------------
    if (
        instance.review_decision == "approved"
        and previous_review != "approved"
    ):
        Notification.objects.get_or_create(
            recipient=instance.owner,
            notif_type="review",
            work_item=instance,
            title="Work Approved",
            defaults={
                "message": (
                    f"Your submission for "
                    f"'{instance.workcycle.title}' has been approved."
                )
            }
        )

    # -----------------------------
    # REVISION ACCEPTED
    # -----------------------------
    if (
        instance.review_decision == "approved"
        and previous_review == "revision"
    ):
        Notification.objects.get_or_create(
            recipient=instance.owner,
            notif_type="review",
            work_item=instance,
            title="Revision Accepted",
            defaults={
                "message": (
                    f"Your revised submission for "
                    f"'{instance.workcycle.title}' was accepted."
                )
            }
        )


# =====================================================
# SUBMISSION MARKED LATE
# =====================================================
@receiver(post_save, sender=WorkItem)
def notify_submission_late(sender, instance, created, **kwargs):
    if (
        instance.status == "done"
        and instance.submitted_at
        and instance.submitted_at > instance.workcycle.due_at
    ):
        Notification.objects.get_or_create(
            recipient=instance.owner,
            notif_type="reminder",
            work_item=instance,
            title="Submission Marked Late",
            defaults={
                "message": (
                    f"Your submission for "
                    f"'{instance.workcycle.title}' was marked as late."
                )
            }
        )


# =====================================================
# WORK ITEM ARCHIVED
# =====================================================
@receiver(post_save, sender=WorkItem)
def notify_workitem_archived(sender, instance, created, **kwargs):
    if (
        not instance.is_active
        and instance.inactive_reason == "archived"
    ):
        Notification.objects.get_or_create(
            recipient=instance.owner,
            notif_type="system",
            work_item=instance,
            title="Work Archived",
            defaults={
                "message": (
                    f"Your work item for "
                    f"'{instance.workcycle.title}' has been archived."
                )
            }
        )


# =====================================================
# WORK CYCLE CLOSED
# =====================================================
@receiver(post_save, sender=WorkCycle)
def notify_workcycle_closed(sender, instance, created, **kwargs):
    if not instance.is_active:
        for item in instance.work_items.select_related("owner"):
            Notification.objects.get_or_create(
                recipient=item.owner,
                notif_type="system",
                title="Work Cycle Closed",
                defaults={
                    "message": (
                        f"The work cycle "
                        f"'{instance.title}' has been closed."
                    )
                }
            )


# =====================================================
# WORK REASSIGNED
# =====================================================
@receiver(post_save, sender=WorkItem)
def notify_work_reassignment(sender, instance, created, **kwargs):
    if instance.inactive_reason == "reassigned":
        Notification.objects.get_or_create(
            recipient=instance.owner,
            notif_type="system",
            work_item=instance,
            title="Work Reassigned",
            defaults={
                "message": (
                    f"The work for "
                    f"'{instance.workcycle.title}' has been reassigned."
                )
            }
        )
