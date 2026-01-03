"""
notifications/services/reminders/workitem.py

Scheduled reminders for WorkItem owners.
Works alongside real-time signals as a catch-all.
"""

from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from accounts.models import WorkItem
from notifications.models import Notification


# WorkItem milestones (user notifications)
WORKITEM_MILESTONES = {
    7: "7 days left",
    5: "5 days left",
    3: "3 days left",
    1: "1 day left",
    0: "Due today",
}


def send_workitem_deadline_reminders():
    """
    Sends deadline reminders for active work items.
    """
    today = timezone.localdate()
    notification_count = 0

    items = (
        WorkItem.objects
        .select_related("workcycle", "owner")
        .filter(
            is_active=True,
            workcycle__is_active=True,
            workcycle__due_at__date__gte=today,
        )
    )

    for wi in items:
        due_date = wi.workcycle.due_at.date()
        days_remaining = (due_date - today).days

        if days_remaining not in WORKITEM_MILESTONES:
            continue

        if wi.status == "done" and days_remaining > 0:
            continue

        if not wi.owner.email:
            continue

        label = WORKITEM_MILESTONES[days_remaining]
        title = f"Work item due: {label}"

        # -------------------------
        # IN-APP MESSAGE
        # -------------------------
        if days_remaining > 0:
            day_word = "day" if days_remaining == 1 else "days"
            in_app_message = (
                f'Your work item for "{wi.workcycle.title}" '
                f'is due in {days_remaining} {day_word}.'
            )
            priority = Notification.Priority.WARNING
        else:
            if wi.status == "done":
                in_app_message = (
                    f'Your work item for "{wi.workcycle.title}" was due today '
                    f'(submitted).'
                )
            else:
                in_app_message = (
                    f'Your work item for "{wi.workcycle.title}" is due today.'
                )
            priority = Notification.Priority.DANGER

        notification, created = Notification.objects.get_or_create(
            recipient=wi.owner,
            category=Notification.Category.REMINDER,
            work_item=wi,
            title=title,
            defaults={
                "priority": priority,
                "message": in_app_message,
                "workcycle": wi.workcycle,
            },
        )

        notification_count += 1

        if not created:
            continue

        # -------------------------
        # EMAIL
        # -------------------------
        if days_remaining > 0:
            email_subject = "Reminder: Work Item Submission Deadline"
            email_body = (
                "Good day.\n\n"
                "This is a reminder regarding your assigned work item under the work cycle "
                f'"{wi.workcycle.title}".\n\n'
                "The submission deadline is on "
                f"{wi.workcycle.due_at:%A, %d %B %Y}.\n"
                f"Time remaining before the deadline: {label}.\n\n"
                "Please ensure that the required work is completed and submitted "
                "within the prescribed period.\n\n"
                "This notice is issued for your guidance and appropriate action.\n\n"
                "— PENRO WSTI System"
            )
        else:
            if wi.status == "done":
                email_subject = "Notice: Work Item Submission Confirmed (Due Today)"
                email_body = (
                    "Good day.\n\n"
                    "This is to confirm that your work item under the work cycle "
                    f'"{wi.workcycle.title}" was due today, '
                    f"{wi.workcycle.due_at:%A, %d %B %Y}.\n\n"
                    "Your submission has been recorded and is now pending review.\n\n"
                    "Thank you for completing your assigned work within the deadline.\n\n"
                    "— PENRO WSTI System"
                )
            else:
                email_subject = "Notice: Work Item Submission Due Today"
                email_body = (
                    "Good day.\n\n"
                    "This is to inform you that the submission deadline for your assigned work item "
                    "under the work cycle "
                    f'"{wi.workcycle.title}" is today, '
                    f"{wi.workcycle.due_at:%A, %d %B %Y}.\n\n"
                    "Please ensure that the required submission is completed within the day, "
                    "in accordance with established guidelines.\n\n"
                    "This notice is issued for your immediate attention.\n\n"
                    "— PENRO WSTI System"
                )

        send_mail(
            subject=email_subject,
            message=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[wi.owner.email],
            fail_silently=not settings.DEBUG,
        )

    return notification_count
