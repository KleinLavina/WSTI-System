from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from accounts.models import WorkCycle
from notifications.models import Notification


# ============================================================
# WORK CYCLE DEADLINE MILESTONES (DAYS REMAINING)
# ============================================================

WORKCYCLE_MILESTONES = {
    3: "3 days left",
    0: "Due today",
}


# ============================================================
# SEND WORK CYCLE DEADLINE REMINDERS
# ============================================================

def send_workcycle_deadline_reminders():
    """
    Sends deadline reminders for active work cycles.

    In-app notification:
    - Short, old-style text

    Email (Gmail SMTP):
    - Formal, government-standard text
    - Sent only when notification is newly created

    Recipients:
    - Assigned users (via active WorkItems)
    - WorkCycle creator (admin)
    """

    today = timezone.localdate()

    active_cycles = WorkCycle.objects.filter(
        is_active=True,
        due_at__date__gte=today,
    )

    for wc in active_cycles:
        due_date = wc.due_at.date()
        days_remaining = (due_date - today).days

        # Only trigger on defined milestones
        if days_remaining not in WORKCYCLE_MILESTONES:
            continue

        label = WORKCYCLE_MILESTONES[days_remaining]

        # --------------------------------------------------
        # IN-APP NOTIFICATION (OLD / SHORT STYLE)
        # --------------------------------------------------
        title = f"Work cycle due: {label}"

        if days_remaining > 0:
            in_app_message_user = f"“{wc.title}” is due in {days_remaining} day(s)."
            in_app_message_admin = (
                f"The work cycle “{wc.title}” you created "
                f"is due in {days_remaining} day(s)."
            )
        else:
            in_app_message_user = f"“{wc.title}” is due today."
            in_app_message_admin = (
                f"The work cycle “{wc.title}” you created is due today."
            )

        # =====================================================
        # 1. REMIND ASSIGNED USERS (VIA ACTIVE WORK ITEMS)
        # =====================================================
        user_ids = (
            wc.work_items
            .filter(is_active=True)
            .values_list("owner_id", flat=True)
            .distinct()
        )

        for user_id in user_ids:
            notification, created = Notification.objects.get_or_create(
                recipient_id=user_id,
                category=Notification.Category.REMINDER,
                workcycle=wc,
                title=title,  # Dedup key
                defaults={
                    "priority": Notification.Priority.WARNING,
                    "message": in_app_message_user,
                },
            )

            # -------------------------------
            # EMAIL (FORMAL – USERS)
            # -------------------------------
            if not created:
                continue

            user = notification.recipient
            if not user.email:
                continue

            if days_remaining > 0:
                email_subject = "Reminder: Work Cycle Submission Deadline"
                email_body = (
                    f"Good day.\n\n"
                    f"This is a reminder regarding the work cycle "
                    f"“{wc.title}”.\n\n"
                    f"The submission deadline is on "
                    f"{wc.due_at:%A, %d %B %Y}.\n"
                    f"Time remaining before the deadline: {label}.\n\n"
                    f"Please ensure that all required work items under this work cycle "
                    f"are completed and submitted within the prescribed period.\n\n"
                    f"This notice is issued for your guidance and appropriate action.\n\n"
                    f"— PENRO WSTI System"
                )
            else:
                email_subject = "Notice: Work Cycle Submission Due Today"
                email_body = (
                    f"Good day.\n\n"
                    f"This is to inform you that the submission deadline for the work cycle "
                    f"“{wc.title}” is today, {wc.due_at:%A, %d %B %Y}.\n\n"
                    f"Please ensure that all required submissions are completed within the day, "
                    f"in accordance with established guidelines.\n\n"
                    f"This notice is issued for your immediate attention.\n\n"
                    f"— PENRO WSTI System"
                )

            send_mail(
                subject=email_subject,
                message=email_body,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=True,
            )

        # =====================================================
        # 2. REMIND THE CREATOR (ADMIN)
        # =====================================================
        if wc.created_by:
            admin_notification, admin_created = Notification.objects.get_or_create(
                recipient=wc.created_by,
                category=Notification.Category.REMINDER,
                workcycle=wc,
                title=title,  # Same dedup key
                defaults={
                    "priority": Notification.Priority.WARNING,
                    "message": in_app_message_admin,
                },
            )

            # -------------------------------
            # EMAIL (FORMAL – ADMIN)
            # -------------------------------
            if admin_created and wc.created_by.email:
                if days_remaining > 0:
                    admin_email_subject = "Reminder: Work Cycle Deadline (Administrative)"
                    admin_email_body = (
                        f"Good day.\n\n"
                        f"This is a reminder that the work cycle "
                        f"“{wc.title}”, which you created, "
                        f"is scheduled for submission on "
                        f"{wc.due_at:%A, %d %B %Y}.\n\n"
                        f"Time remaining before the deadline: {label}.\n\n"
                        f"This notice is issued for monitoring and administrative reference.\n\n"
                        f"— PENRO WSTI System"
                    )
                else:
                    admin_email_subject = "Notice: Work Cycle Due Today (Administrative)"
                    admin_email_body = (
                        f"Good day.\n\n"
                        f"This is to inform you that the work cycle "
                        f"“{wc.title}”, which you created, "
                        f"is due today, {wc.due_at:%A, %d %B %Y}.\n\n"
                        f"This notice is issued for your immediate awareness and "
                        f"any necessary administrative action.\n\n"
                        f"— PENRO WSTI System"
                    )

                send_mail(
                    subject=admin_email_subject,
                    message=admin_email_body,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[wc.created_by.email],
                    fail_silently=True,
                )
