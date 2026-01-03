"""
notifications/signals/reminders.py

Real-time deadline reminder signals.
Handles immediate notifications when due_at changes.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import WorkCycle, WorkItem
from notifications.models import Notification


# ============================================================
# MILESTONE DEFINITIONS (MUST MATCH SERVICE FILES)
# ============================================================

WORKCYCLE_MILESTONES = {
    5: "5 days left",
    3: "3 days left",
    1: "1 day left",
    0: "Due today",
}

WORKITEM_MILESTONES = {
    7: "7 days left",
    5: "5 days left",
    3: "3 days left",
    1: "1 day left",
    0: "Due today",
}


# ============================================================
# HELPER: GET CURRENT MILESTONE
# ============================================================

def get_current_milestone(due_at, milestone_dict):
    """
    Returns the milestone label if we're within a reminder window.
    Returns None if no milestone applies.
    """
    today = timezone.localdate()
    due_date = due_at.date()
    days_remaining = (due_date - today).days

    return milestone_dict.get(days_remaining)


# ============================================================
# PRE_SAVE: TRACK IF DUE_AT CHANGED
# ============================================================

@receiver(pre_save, sender=WorkCycle)
def track_workcycle_due_change(sender, instance, **kwargs):
    """
    Track if due_at changed before save.
    Sets a flag that post_save can check.
    """
    if not instance.pk:
        instance._due_at_changed = True
        return

    try:
        old_instance = WorkCycle.objects.get(pk=instance.pk)
        instance._due_at_changed = (old_instance.due_at != instance.due_at)
    except WorkCycle.DoesNotExist:
        instance._due_at_changed = True


# ============================================================
# WORKCYCLE: NOTIFY ADMIN ONLY WHEN DUE_AT CHANGES
# ============================================================

@receiver(post_save, sender=WorkCycle)
def handle_workcycle_due_change(sender, instance, created, **kwargs):
    """
    Notify creator (admin) when due_at changes and hits a milestone.
    """
    if not instance.created_by or not instance.is_active:
        return

    if not created and not getattr(instance, "_due_at_changed", False):
        return

    milestone = get_current_milestone(instance.due_at, WORKCYCLE_MILESTONES)
    if not milestone:
        return

    days_remaining = (instance.due_at.date() - timezone.localdate()).days
    title = f"Work cycle due: {milestone}"
    priority = (
        Notification.Priority.WARNING
        if days_remaining > 0
        else Notification.Priority.DANGER
    )

    if days_remaining > 0:
        day_word = "day" if days_remaining == 1 else "days"
        message = (
            f'The work cycle "{instance.title}" you created '
            f'is due in {days_remaining} {day_word}.'
        )
    else:
        message = (
            f'The work cycle "{instance.title}" you created is due today.'
        )

    Notification.objects.update_or_create(
        recipient=instance.created_by,
        category=Notification.Category.REMINDER,
        workcycle=instance,
        title=title,
        defaults={
            "priority": priority,
            "message": message,
            "is_read": False,
        },
    )


# ============================================================
# WORKITEM: INDIVIDUAL REMINDERS WHEN DUE_AT CHANGES
# ============================================================

@receiver(post_save, sender=WorkCycle)
def handle_workitem_due_cascade(sender, instance, created, **kwargs):
    """
    Update WorkItem reminders when WorkCycle due_at changes.
    """
    if not instance.is_active:
        return

    if not created and not getattr(instance, "_due_at_changed", False):
        return

    milestone = get_current_milestone(instance.due_at, WORKITEM_MILESTONES)
    if not milestone:
        return

    days_remaining = (instance.due_at.date() - timezone.localdate()).days
    title = f"Work item due: {milestone}"
    priority = (
        Notification.Priority.WARNING
        if days_remaining > 0
        else Notification.Priority.DANGER
    )

    work_items = (
        WorkItem.objects
        .filter(workcycle=instance, is_active=True)
        .exclude(status="done")
        .select_related("owner")
    )

    for wi in work_items:
        if not wi.owner.email:
            continue

        if days_remaining > 0:
            day_word = "day" if days_remaining == 1 else "days"
            message = (
                f'Your work item for "{wi.workcycle.title}" '
                f'is due in {days_remaining} {day_word}.'
            )
        else:
            message = (
                f'Your work item for "{wi.workcycle.title}" is due today.'
            )

        Notification.objects.update_or_create(
            recipient=wi.owner,
            category=Notification.Category.REMINDER,
            work_item=wi,
            title=title,
            defaults={
                "priority": priority,
                "message": message,
                "workcycle": wi.workcycle,
                "is_read": False,
            },
        )


# ============================================================
# WORKITEM: CLEAR REMINDERS WHEN SUBMITTED
# ============================================================

@receiver(post_save, sender=WorkItem)
def clear_reminders_on_submission(sender, instance, created, **kwargs):
    """
    When WorkItem is submitted, remove its reminders.
    """
    if instance.status == "done":
        Notification.objects.filter(
            recipient=instance.owner,
            category=Notification.Category.REMINDER,
            work_item=instance,
        ).delete()


# ============================================================
# CLEANUP: REMOVE STALE REMINDERS WHEN WORKCYCLE DEACTIVATED
# ============================================================

@receiver(post_save, sender=WorkCycle)
def cleanup_reminders_on_deactivation(sender, instance, **kwargs):
    """
    Remove all reminders when WorkCycle is deactivated.
    """
    if not instance.is_active:
        Notification.objects.filter(
            category=Notification.Category.REMINDER,
            workcycle=instance,
        ).delete()
