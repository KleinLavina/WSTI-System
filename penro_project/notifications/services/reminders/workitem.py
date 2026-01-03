from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from accounts.models import WorkItem
from notifications.models import Notification


WORKITEM_MILESTONES = {
    7: "7 days left",
    5: "5 days left",
    3: "3 days left",
    1: "1 day left",
    0: "Due today",
}


def send_workitem_deadline_reminders():
    today = timezone.localdate()

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

        # Skip advance reminders if already submitted
        if days_remaining > 0 and wi.status == "done":
            continue

        if not wi.owner.email:
            continue

        label = WORKITEM_MILESTONES[days_remaining]

        # --------------------------------------------------
        # IN-APP NOTIFICATION (OLD / SHORT STYLE)
        # --------------------------------------------------
        title = f"Work item due: {label}"

        if days_remaining > 0:
            in_app_message = (
                f"Your work item for “{wi.workcycle.title}” "
                f"is due in {days_remaining} day(s)."
            )
        else:
            in_app_message = (
                f"Your work item for “{wi.workcycle.title}” is due today."
            )

        notification, created = Notification.objects.get_or_create(
            recipient=wi.owner,
            category=Notification.Category.REMINDER,
            work_item=wi,
            title=title,  # Dedup key
            defaults={
                "priority": Notification.Priority.WARNING,
                "message": in_app_message,
                "workcycle": wi.workcycle,
            },
        )

        # --------------------------------------------------
        # EMAIL (FORMAL / GOVERNMENT STYLE)
        # --------------------------------------------------
        # Only send email if notification was newly created
        if not created:
            continue

        if days_remaining > 0:
            email_subject = "Reminder: Work Item Submission Deadline"
            email_body = (
                f"Good day.\n\n"
                f"This is a reminder regarding your assigned work item under the work cycle "
                f"“{wi.workcycle.title}”.\n\n"
                f"The submission deadline is on "
                f"{wi.workcycle.due_at:%A, %d %B %Y}.\n"
                f"Time remaining before the deadline: {label}.\n\n"
                f"Please ensure that the required work is completed and submitted "
                f"within the prescribed period.\n\n"
                f"This notice is issued for your guidance and appropriate action.\n\n"
                f"— PENRO WSTI System"
            )
        else:
            email_subject = "Notice: Work Item Submission Due Today"
            email_body = (
                f"Good day.\n\n"
                f"This is to inform you that the submission deadline for your assigned work item "
                f"under the work cycle “{wi.workcycle.title}” is today, "
                f"{wi.workcycle.due_at:%A, %d %B %Y}.\n\n"
                f"Please ensure that the required submission is completed within the day, "
                f"in accordance with established guidelines.\n\n"
                f"This notice is issued for your immediate attention.\n\n"
                f"— PENRO WSTI System"
            )

        send_mail(
            subject=email_subject,
            message=email_body,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[wi.owner.email],
            fail_silently=True,
        )
