"""
notifications/services/reminders/workcycle.py

Work Cycle deadline reminders.
Notifies ONLY the admin/creator for monitoring purposes.

Users get their notifications via WorkItem reminders instead.
"""

from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from accounts.models import WorkCycle
from notifications.models import Notification


# WorkCycle milestones (admin monitoring)
WORKCYCLE_MILESTONES = {
    5: "5 days left",
    3: "3 days left",
    1: "1 day left",
    0: "Due today",
}


def send_workcycle_deadline_reminders():
    """
    Sends deadline reminders for active work cycles.

    Recipients:
    - WorkCycle creator (admin/creator ONLY) - for monitoring

    Milestones: 5, 3, 1, 0 days

    Returns: Count of notifications created
    """
    today = timezone.localdate()
    notification_count = 0

    active_cycles = WorkCycle.objects.filter(
        is_active=True,
        due_at__date__gte=today,
        created_by__isnull=False,
    )

    for wc in active_cycles:
        due_date = wc.due_at.date()
        days_remaining = (due_date - today).days

        if days_remaining not in WORKCYCLE_MILESTONES:
            continue

        label = WORKCYCLE_MILESTONES[days_remaining]
        title = f"Work cycle due: {label}"

        # --------------------------------------------------
        # IN-APP MESSAGE (ADMIN)
        # --------------------------------------------------
        if days_remaining > 0:
            day_word = "day" if days_remaining == 1 else "days"
            message = (
                f'The work cycle "{wc.title}" you created '
                f'is due in {days_remaining} {day_word}.'
            )
            priority = Notification.Priority.WARNING
        else:
            message = (
                f'The work cycle "{wc.title}" you created is due today.'
            )
            priority = Notification.Priority.DANGER

        notification, created = Notification.objects.get_or_create(
            recipient=wc.created_by,
            category=Notification.Category.REMINDER,
            workcycle=wc,
            title=title,
            defaults={
                "priority": priority,
                "message": message,
            },
        )

        notification_count += 1

        # --------------------------------------------------
        # EMAIL (ONLY IF NEW NOTIFICATION)
        # --------------------------------------------------
        if not created:
            continue

        if not wc.created_by.email:
            continue

        if days_remaining > 0:
            email_subject = "Reminder: Work Cycle Deadline (Administrative)"
            email_body = (
                "Good day.\n\n"
                "This is a reminder that the work cycle "
                f'"{wc.title}", which you created, '
                "is scheduled for submission on "
                f"{wc.due_at:%A, %d %B %Y}.\n\n"
                f"Time remaining before the deadline: {label}.\n\n"
                "This notice is issued for monitoring and "
                "administrative reference.\n\n"
                "— PENRO WSTI System"
            )
        else:
            email_subject = "Notice: Work Cycle Due Today (Administrative)"
            email_body = (
                "Good day.\n\n"
                "This is to inform you that the work cycle "
                f'"{wc.title}", which you created, '
                "is due today, "
                f"{wc.due_at:%A, %d %B %Y}.\n\n"
                "This notice is issued for your immediate "
                "awareness and any necessary administrative action.\n\n"
                "— PENRO WSTI System"
            )

        send_mail(
            subject=email_subject,
            message=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[wc.created_by.email],
            fail_silently=not settings.DEBUG,
        )

    return notification_count
