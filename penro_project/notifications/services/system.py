from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from notifications.models import Notification
from accounts.models import WorkCycle

User = get_user_model()


# ============================================================
# WORK CYCLE EDITED (SYSTEM)
# ============================================================

def notify_workcycle_edited(
    *,
    workcycle: WorkCycle,
    edited_by,
    old_due_at=None,
):
    """
    SYSTEM notification when a work cycle is edited.

    - In-app notification (SYSTEM category)
    - Email notification (Gmail SMTP)
    - Sent to:
        - Assigned users
        - WorkCycle creator (admin)
    """

    # --------------------------------------------------
    # BUILD CHANGE SUMMARY
    # --------------------------------------------------
    changes = []

    if old_due_at and old_due_at != workcycle.due_at:
        changes.append(
            f"Due date changed from "
            f"{old_due_at:%d %B %Y} to {workcycle.due_at:%d %B %Y}"
        )

    if not changes:
        changes.append("Work cycle details were updated")

    change_summary = "; ".join(changes)

    # --------------------------------------------------
    # COMMON CONTENT
    # --------------------------------------------------
    title = "Work cycle updated"

    in_app_message = (
        f"The work cycle “{workcycle.title}” has been updated. "
        f"{change_summary}."
    )

    email_subject = "Notice: Work Cycle Updated"

    editor_name = (
        edited_by.get_full_name()
        if edited_by and edited_by.get_full_name()
        else getattr(edited_by, "username", "System")
    )

    email_body = (
        f"Good day.\n\n"
        f"This is to inform you that the work cycle "
        f"“{workcycle.title}” has been updated.\n\n"
        f"Summary of changes:\n"
        f"- {change_summary}\n\n"
        f"Updated by: {editor_name}\n"
        f"Date of update: {timezone.localtime():%A, %d %B %Y}\n\n"
        f"This notice is issued for your information.\n\n"
        f"— PENRO WSTI System"
    )

    # =====================================================
    # 1. ASSIGNED USERS (VIA ACTIVE WORK ITEMS)
    # =====================================================
    user_ids = (
        workcycle.work_items
        .filter(is_active=True)
        .values_list("owner_id", flat=True)
        .distinct()
    )

    recipients = User.objects.filter(
        id__in=user_ids,
        is_active=True,
    )

    for user in recipients:
        notification, created = Notification.objects.get_or_create(
            recipient=user,
            category=Notification.Category.SYSTEM,
            workcycle=workcycle,
            title=title,
            defaults={
                "priority": Notification.Priority.INFO,
                "message": in_app_message,
            },
        )

        if created and user.email:
            send_mail(
                subject=email_subject,
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )

    # =====================================================
    # 2. CREATOR (ADMIN)
    # =====================================================
    if workcycle.created_by:
        admin = workcycle.created_by

        admin_notification, admin_created = Notification.objects.get_or_create(
            recipient=admin,
            category=Notification.Category.SYSTEM,
            workcycle=workcycle,
            title=title,
            defaults={
                "priority": Notification.Priority.INFO,
                "message": in_app_message,
            },
        )

        if admin_created and admin.email:
            send_mail(
                subject=email_subject,
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin.email],
                fail_silently=True,
            )

def notify_workcycle_archive_toggled(
    *,
    workcycle: WorkCycle,
    actor,
):
    """
    SYSTEM in-app notification when a work cycle is
    archived or restored.

    - IN-APP ONLY (no email)
    - Sent to:
        - Assigned users
        - WorkCycle creator (admin)
        - Admin who performed the action (actor)
    """

    is_restored = workcycle.is_active

    # --------------------------------------------------
    # CONTENT
    # --------------------------------------------------
    title = (
        "Work cycle restored"
        if is_restored
        else "Work cycle archived"
    )

    if is_restored:
        base_message = (
            f"The work cycle “{workcycle.title}” has been restored "
            f"and is now active."
        )
    else:
        base_message = (
            f"The work cycle “{workcycle.title}” has been archived "
            f"and is no longer active."
        )

    actor_message = (
        f"You {'restored' if is_restored else 'archived'} "
        f"the work cycle “{workcycle.title}”."
    )

    # =====================================================
    # 1. ASSIGNED USERS
    # =====================================================
    user_ids = (
        workcycle.work_items
        .values_list("owner_id", flat=True)
        .distinct()
    )

    recipients = User.objects.filter(
        id__in=user_ids,
        is_active=True,
    )

    for user in recipients:
        Notification.objects.get_or_create(
            recipient=user,
            category=Notification.Category.SYSTEM,
            workcycle=workcycle,
            title=title,
            defaults={
                "priority": Notification.Priority.INFO,
                "message": base_message,
            },
        )

    # =====================================================
    # 2. CREATOR (ADMIN)
    # =====================================================
    if workcycle.created_by:
        Notification.objects.get_or_create(
            recipient=workcycle.created_by,
            category=Notification.Category.SYSTEM,
            workcycle=workcycle,
            title=title,
            defaults={
                "priority": Notification.Priority.INFO,
                "message": base_message,
            },
        )

    # =====================================================
    # 3. ACTOR (ADMIN WHO TOGGLED)
    # =====================================================
    Notification.objects.get_or_create(
        recipient=actor,
        category=Notification.Category.SYSTEM,
        workcycle=workcycle,
        title=title,
        defaults={
            "priority": Notification.Priority.INFO,
            "message": actor_message,
        },
    )

def notify_workcycle_deleted(
    *,
    workcycle_title: str,
    actor,
    affected_user_ids,
):
    """
    SYSTEM in-app notification when a work cycle
    is permanently deleted.

    - IN-APP ONLY
    - Sent to:
        - Assigned users (former)
        - No email
    """

    title = "Work cycle deleted"

    message = (
        f"The work cycle “{workcycle_title}” has been permanently deleted "
        f"by an administrator."
    )

    recipients = User.objects.filter(
        id__in=affected_user_ids,
        is_active=True,
    )

    for user in recipients:
        Notification.objects.create(
            recipient=user,
            category=Notification.Category.SYSTEM,
            priority=Notification.Priority.WARNING,
            title=title,
            message=message,
            workcycle=None,  # important: object no longer exists
        )

