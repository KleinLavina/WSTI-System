# notifications/signals/admin_notification_signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import WorkItem, WorkItemMessage, User
from notifications.models import Notification
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import WorkItem, WorkItemMessage, WorkCycle
from notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=WorkItem)
def notify_admin_work_submitted(sender, instance, created, **kwargs):
    """
    🔴 High
    Trigger: WorkItem status changes to DONE
    """
    if instance.status == "done" and instance.submitted_at:
        admins = User.objects.filter(login_role="admin", is_active=True)

        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                notif_type="status",
                title="Work Submitted",
                message=f"{instance.owner} submitted work for '{instance.workcycle}'.",
                work_item=instance,
            )

@receiver(post_save, sender=WorkItem)
def notify_admin_late_submission(sender, instance, created, **kwargs):
    """
    🔴 High
    Trigger: Submitted AFTER due date
    """
    if (
        instance.status == "done"
        and instance.submitted_at
        and instance.workcycle
        and instance.submitted_at > instance.workcycle.due_at
    ):
        admins = User.objects.filter(login_role="admin", is_active=True)

        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                notif_type="reminder",
                title="Late Submission",
                message=(
                    f"{instance.owner} submitted work late "
                    f"for '{instance.workcycle}'."
                ),
                work_item=instance,
            )

def notify_admin_missed_deadlines():
    """
    🔴 CRITICAL
    Trigger: Due date passed AND work not submitted
    """
    now = timezone.now()

    overdue_items = WorkItem.objects.filter(
        status__in=["not_started", "working_on_it"],
        workcycle__due_at__lt=now,
        is_active=True,
    )

    admins = User.objects.filter(login_role="admin", is_active=True)

    for item in overdue_items:
        for admin in admins:
            Notification.objects.get_or_create(
                recipient=admin,
                notif_type="reminder",
                title="Missed Deadline",
                message=(
                    f"{item.owner} missed the deadline "
                    f"for '{item.workcycle}'."
                ),
                work_item=item,
            )

@receiver(post_save, sender=WorkItemMessage)
def notify_admin_new_message(sender, instance, created, **kwargs):
    """
    🟠 Medium
    Trigger: New message created
    """
    if not created:
        return

    admins = User.objects.filter(login_role="admin", is_active=True)

    for admin in admins:
        Notification.objects.create(
            recipient=admin,
            notif_type="chat",
            title="New Work Item Message",
            message=(
                f"New message from {instance.sender} "
                f"on '{instance.work_item.workcycle}'."
            ),
            work_item=instance.work_item,
        )

@receiver(post_save, sender=WorkItem)
def admin_revision_resubmitted(sender, instance, created, **kwargs):
    if created:
        return

    # Resubmitted after revision
    if instance.review_decision == "pending" and instance.status == "done":
        admins = User.objects.filter(login_role="admin")

        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                notif_type="review",
                title="Revision Resubmitted",
                message=(
                    f"{instance.owner.get_full_name() or instance.owner.username} "
                    f"has resubmitted a revised work item."
                ),
                work_item=instance
            )

@receiver(post_save, sender=WorkItem)
def admin_cycle_completed(sender, instance, created, **kwargs):
    workcycle = instance.workcycle

    # Only check when something becomes done
    if instance.status != "done":
        return

    total_items = workcycle.work_items.count()
    done_items = workcycle.work_items.filter(status="done").count()

    if total_items > 0 and total_items == done_items:
        admins = User.objects.filter(login_role="admin")

        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                notif_type="system",
                title="Work Cycle Completed",
                message=f"All work items for '{workcycle.title}' have been completed."
            )

def notify_admin_deadline_near():
    now = timezone.now()
    threshold = now + timezone.timedelta(days=2)

    upcoming_cycles = WorkCycle.objects.filter(
        due_at__lte=threshold,
        due_at__gte=now,
        is_active=True
    )

    admins = User.objects.filter(login_role="admin")

    for cycle in upcoming_cycles:
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                notif_type="reminder",
                title="Upcoming Deadline",
                message=f"The deadline for '{cycle.title}' is approaching."
            )

@receiver(post_save, sender=WorkItem)
def admin_auto_system_action(sender, instance, created, **kwargs):
    if instance.inactive_reason == "archived":
        admins = User.objects.filter(login_role="admin")

        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                notif_type="system",
                title="System Action Performed",
                message=(
                    f"The system automatically archived a work item "
                    f"from '{instance.workcycle.title}'."
                ),
                work_item=instance
            )
