# notifications/signals/userInformational_notification_signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from notifications.models import Notification
from accounts.models import WorkItem, WorkCycle


# =====================================================
# 8 & 9. WORK REVIEWED (APPROVED / REVISION ACCEPTED)
# =====================================================
@receiver(post_save, sender=WorkItem)
def notify_user_review_result(sender, instance, created, **kwargs):
    if created:
        return

    # Approved
    if instance.review_decision == "approved":
        Notification.objects.get_or_create(
            recipient=instance.owner,
            notif_type="review",
            work_item=instance,
            title="Work Approved",
            defaults={
                "message": f"Your submission for '{instance.workcycle.title}' has been approved."
            }
        )

    # Revision accepted (was revision before, now approved)
    if instance.review_decision == "approved" and instance.revision_count > 0:
        Notification.objects.get_or_create(
            recipient=instance.owner,
            notif_type="review",
            work_item=instance,
            title="Revision Accepted",
            defaults={
                "message": f"Your revised submission for '{instance.workcycle.title}' was accepted."
            }
        )


# =====================================================
# 10. SUBMISSION MARKED LATE (INFORMATIONAL)
# =====================================================
@receiver(post_save, sender=WorkItem)
def notify_submission_late(sender, instance, created, **kwargs):
    if instance.status == "done" and instance.submitted_at:
        if instance.submitted_at > instance.workcycle.due_at:
            Notification.objects.get_or_create(
                recipient=instance.owner,
                notif_type="reminder",
                work_item=instance,
                title="Submission Marked Late",
                defaults={
                    "message": f"Your submission for '{instance.workcycle.title}' was marked as late."
                }
            )


# =====================================================
# 11. WORK ITEM ARCHIVED
# =====================================================
@receiver(post_save, sender=WorkItem)
def notify_workitem_archived(sender, instance, created, **kwargs):
    if not instance.is_active and instance.inactive_reason == "archived":
        Notification.objects.get_or_create(
            recipient=instance.owner,
            notif_type="system",
            work_item=instance,
            title="Work Archived",
            defaults={
                "message": f"Your work item for '{instance.workcycle.title}' has been archived."
            }
        )


# =====================================================
# 12. WORK CYCLE CLOSED
# =====================================================
@receiver(post_save, sender=WorkCycle)
def notify_workcycle_closed(sender, instance, created, **kwargs):
    if not instance.is_active:
        work_items = instance.work_items.select_related("owner")
        for item in work_items:
            Notification.objects.get_or_create(
                recipient=item.owner,
                notif_type="system",
                title="Work Cycle Closed",
                defaults={
                    "message": f"The work cycle '{instance.title}' has been closed."
                }
            )


# =====================================================
# 13 & 14. WORK REASSIGNED
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
                "message": f"The work for '{instance.workcycle.title}' has been reassigned."
            }
        )
