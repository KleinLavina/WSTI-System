# notifications/signals/userActReq_notification_views.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import (
    WorkAssignment,
    WorkItem,
    WorkItemMessage,
)
from notifications.models import Notification


# ============================================================
# 1. USER ASSIGNED TO WORK CYCLE
# ============================================================

@receiver(post_save, sender=WorkAssignment)
def notify_user_assigned_to_workcycle(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.assigned_user:
        Notification.objects.create(
            recipient=instance.assigned_user,
            notif_type="system",
            title="New Work Assigned",
            message=f"You have been assigned to '{instance.workcycle.title}'.",
        )


# ============================================================
# 2. WORK ITEM AUTO-CREATED FOR USER
# ============================================================

@receiver(post_save, sender=WorkItem)
def notify_workitem_created(sender, instance, created, **kwargs):
    if not created:
        return

    Notification.objects.create(
        recipient=instance.owner,
        notif_type="system",
        title="Work Item Created",
        message=f"A work item for '{instance.workcycle.title}' is now available.",
        work_item=instance,
    )


# ============================================================
# 3. REVISION REQUESTED (ACTION REQUIRED)
# ============================================================

@receiver(post_save, sender=WorkItem)
def notify_revision_requested(sender, instance, **kwargs):
    if instance.review_decision == "revision":
        Notification.objects.get_or_create(
            recipient=instance.owner,
            notif_type="review",
            title="Revision Required",
            message="Your submission requires revision. Please update and resubmit.",
            work_item=instance,
        )


# ============================================================
# 4. ADMIN / MANAGER MESSAGE (CHAT)
# ============================================================

@receiver(post_save, sender=WorkItemMessage)
def notify_user_new_message(sender, instance, created, **kwargs):
    if not created:
        return

    # Only notify if sender is admin or manager
    if instance.sender_role in ["admin", "manager"]:
        Notification.objects.create(
            recipient=instance.work_item.owner,
            notif_type="chat",
            title="New Message from Admin",
            message=instance.message[:200],
            work_item=instance.work_item,
        )


# ============================================================
# 5. DEADLINE APPROACHING (DUE SOON)
# ============================================================

def notify_deadline_near(work_item):
    Notification.objects.get_or_create(
        recipient=work_item.owner,
        notif_type="reminder",
        title="Deadline Approaching",
        message=f"The deadline for '{work_item.workcycle.title}' is near.",
        work_item=work_item,
    )


# ============================================================
# 6. MISSED DEADLINE
# ============================================================

def notify_deadline_missed(work_item):
    Notification.objects.get_or_create(
        recipient=work_item.owner,
        notif_type="reminder",
        title="Deadline Missed",
        message=f"You missed the deadline for '{work_item.workcycle.title}'.",
        work_item=work_item,
    )


# ============================================================
# 7. WORK REASSIGNED TO USER
# ============================================================

@receiver(post_save, sender=WorkItem)
def notify_work_reassigned(sender, instance, **kwargs):
    if instance.inactive_reason == "reassigned":
        Notification.objects.create(
            recipient=instance.owner,
            notif_type="system",
            title="Work Reassigned",
            message="A work item has been reassigned to you.",
            work_item=instance,
        )
