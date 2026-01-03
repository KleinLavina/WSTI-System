from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

from notifications.models import Notification

User = get_user_model()


# ============================================================
# ASSIGNMENT NOTIFICATIONS (IN-APP + EMAIL)
# ============================================================

def create_assignment_notifications(
    *,
    user_ids,
    workcycle,
    assigned_by=None,
):
    """
    ASSIGNMENT notifications
    ------------------------
    - In-app notification (bulk)
    - One-time Gmail email per user
    """

    users = User.objects.filter(
        id__in=user_ids,
        is_active=True,
    )

    # -----------------------------
    # IN-APP NOTIFICATIONS (BULK)
    # -----------------------------
    Notification.objects.bulk_create([
        Notification(
            recipient=user,
            category=Notification.Category.ASSIGNMENT,
            priority=Notification.Priority.INFO,
            title="New work assigned",
            message=(
                f"You have been assigned to the work cycle "
                f"“{workcycle.title}”."
            ),
            workcycle=workcycle,
        )
        for user in users
    ])

    # -----------------------------
    # EMAIL NOTIFICATIONS (PER USER)
    # -----------------------------
    for user in users:
        if not user.email:
            continue

        subject = "Notice: New Work Cycle Assignment"

        body = (
            f"Good day.\n\n"
            f"This is to inform you that you have been assigned to the work cycle "
            f"“{workcycle.title}”.\n\n"
            f"Please log in to the system to review the details, requirements, "
            f"and applicable deadlines associated with this assignment.\n\n"
        )

        if assigned_by:
            body += f"This assignment was issued by {assigned_by}.\n\n"

        body += (
            f"This notice is issued for your information and appropriate action.\n\n"
            f"— PENRO WSTI System"
        )

        send_mail(
            subject=subject,
            message=body,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            fail_silently=True,
        )


# ============================================================
# REMOVAL NOTIFICATIONS (IN-APP + EMAIL)
# ============================================================

def create_removal_notifications(
    *,
    user_ids,
    workcycle,
    reason=None,
):
    """
    SYSTEM notifications
    --------------------
    - In-app notification (bulk)
    - One-time Gmail email per user
    """

    users = User.objects.filter(
        id__in=user_ids,
        is_active=True,
    )

    in_app_message = (
        reason
        or f"You were removed from the work cycle “{workcycle.title}”."
    )

    # -----------------------------
    # IN-APP NOTIFICATIONS (BULK)
    # -----------------------------
    Notification.objects.bulk_create([
        Notification(
            recipient=user,
            category=Notification.Category.SYSTEM,
            priority=Notification.Priority.WARNING,
            title="Work assignment changed",
            message=in_app_message,
            workcycle=workcycle,
        )
        for user in users
    ])

    # -----------------------------
    # EMAIL NOTIFICATIONS (PER USER)
    # -----------------------------
    for user in users:
        if not user.email:
            continue

        subject = "Notice: Work Cycle Assignment Update"

        body = (
            f"Good day.\n\n"
            f"This is to inform you that your assignment under the work cycle "
            f"“{workcycle.title}” has been updated and you are no longer included "
            f"in the said work cycle.\n\n"
        )

        if reason:
            body += f"Reason:\n{reason}\n\n"

        body += (
            f"If you require clarification or believe this update was made in error, "
            f"please coordinate with the appropriate administrator.\n\n"
            f"This notice is issued for your information.\n\n"
            f"— PENRO WSTI System"
        )

        send_mail(
            subject=subject,
            message=body,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            fail_silently=True,
        )
