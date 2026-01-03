from django.urls import reverse
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from notifications.models import Notification
from accounts.models import WorkItem


# ============================================================
# WORK ITEM STATUS CHANGED (USER → ADMIN / CREATOR)
# ============================================================

def notify_work_item_status_changed(
    *,
    work_item: WorkItem,
    actor,
    old_status: str | None,
):
    """
    Notify the WorkCycle creator (admin) when a user
    changes the status of a work item.

    Supports:
    - submit (→ done)
    - undo submit (done → working_on_it)
    - normal status changes

    Channels:
    - In-app notification
    - Gmail SMTP email
    """

    # --------------------------------------------------
    # SAFETY GUARDS
    # --------------------------------------------------
    admin = work_item.workcycle.created_by
    if not admin:
        return

    if old_status == work_item.status:
        return

    valid_statuses = {"not_started", "working_on_it", "done"}
    if old_status not in valid_statuses or work_item.status not in valid_statuses:
        return

    actor_name = actor.get_full_name() or actor.username
    wc_title = work_item.workcycle.title

    # --------------------------------------------------
    # DETERMINE TRANSITION
    # --------------------------------------------------
    if old_status != "done" and work_item.status == "done":
        transition = "submitted"

    elif old_status == "done" and work_item.status != "done":
        transition = "submission_reverted"

    else:
        transition = "status_updated"

    # --------------------------------------------------
    # CONTENT
    # --------------------------------------------------
    title = "Work item status update"

    if transition == "submitted":
        message = (
            f"{actor_name} submitted a work item under "
            f"the work cycle “{wc_title}”."
        )
        priority = Notification.Priority.WARNING

        email_subject = "Work Item Submitted"
        email_body = (
            f"Good day.\n\n"
            f"{actor_name} has submitted a work item under the work cycle "
            f"“{wc_title}”.\n\n"
            f"Please review the submission at your convenience.\n\n"
            f"— PENRO WSTI System"
        )

    elif transition == "submission_reverted":
        message = (
            f"{actor_name} reverted a previously submitted work item "
            f"under the work cycle “{wc_title}”."
        )
        priority = Notification.Priority.INFO

        email_subject = "Work Item Submission Reverted"
        email_body = (
            f"Good day.\n\n"
            f"{actor_name} has reverted a previously submitted work item "
            f"under the work cycle “{wc_title}”.\n\n"
            f"This item is now editable again.\n\n"
            f"— PENRO WSTI System"
        )

    else:
        new_label = dict(
            WorkItem._meta.get_field("status").choices
        ).get(work_item.status, work_item.status)

        message = (
            f"{actor_name} updated the status of a work item under "
            f"“{wc_title}” to “{new_label}”."
        )
        priority = Notification.Priority.INFO

        email_subject = "Work Item Status Updated"
        email_body = (
            f"Good day.\n\n"
            f"{actor_name} updated the status of a work item under "
            f"the work cycle “{wc_title}” to “{new_label}”.\n\n"
            f"— PENRO WSTI System"
        )

    # --------------------------------------------------
    # CREATE IN-APP NOTIFICATION (DEDUP SAFE)
    # --------------------------------------------------
    notif, created = Notification.objects.get_or_create(
        recipient=admin,
        category=Notification.Category.STATUS,
        work_item=work_item,
        title=f"{title}: {transition}",  # dedup key
        defaults={
            "priority": priority,
            "message": message,
            "workcycle": work_item.workcycle,
            "action_url": reverse(
                "admin_app:work-item-review",
                args=[work_item.id],
            ),
        },
    )

    # --------------------------------------------------
    # EMAIL (ONLY ON FIRST CREATE)
    # --------------------------------------------------
    if created and admin.email:
        send_mail(
            subject=email_subject,
            message=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin.email],
            fail_silently=True,
        )
