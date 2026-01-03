from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

from notifications.models import Notification
from accounts.models import WorkItem


# ============================================================
# WORK ITEM REVIEW DECISION CHANGED (ADMIN → USER)
# ============================================================

def notify_work_item_review_changed(
    *,
    work_item: WorkItem,
    actor,
    old_decision: str | None,
):
    """
    Notify the work item OWNER when an admin
    changes the review decision.

    Triggers on:
    - approved
    - revision
    - pending (only if reverted)

    Channels:
    - In-app notification
    - Email (SMTP)

    Dedup:
    - Per decision change
    """

    # --------------------------------------------------
    # SAFETY GUARDS
    # --------------------------------------------------
    if not work_item.owner:
        return

    if old_decision == work_item.review_decision:
        return

    if work_item.review_decision not in {"approved", "revision", "pending"}:
        return

    user = work_item.owner

    decision_label = dict(
        WorkItem._meta.get_field("review_decision").choices
    ).get(work_item.review_decision, work_item.review_decision)

    # --------------------------------------------------
    # CONTENT
    # --------------------------------------------------
    title = "Work item review updated"

    if work_item.review_decision == "approved":
        message = (
            f"Your submitted work item under the work cycle "
            f"“{work_item.workcycle.title}” has been approved."
        )
        priority = Notification.Priority.INFO

    elif work_item.review_decision == "revision":
        message = (
            f"Your submitted work item under the work cycle "
            f"“{work_item.workcycle.title}” requires revision."
        )
        priority = Notification.Priority.WARNING

    else:  # reverted to pending
        message = (
            f"The review status of your work item under "
            f"“{work_item.workcycle.title}” has been reverted to pending."
        )
        priority = Notification.Priority.INFO

    # --------------------------------------------------
    # CREATE IN-APP NOTIFICATION
    # --------------------------------------------------
    notification = Notification.objects.create(
        recipient=user,
        category=Notification.Category.REVIEW,
        priority=priority,
        title=title,
        message=message,
        work_item=work_item,
        workcycle=work_item.workcycle,
        action_url=reverse(
            "user_app:work-item-detail",
            args=[work_item.id],
        ),
    )

    # --------------------------------------------------
    # EMAIL (FORMAL / GOVERNMENT STYLE)
    # --------------------------------------------------
    if not user.email:
        return

    if work_item.review_decision == "approved":
        email_subject = "Notice: Work Item Approved"
        email_body = (
            f"Good day.\n\n"
            f"This is to inform you that your submitted work item under the work cycle "
            f"“{work_item.workcycle.title}” has been approved.\n\n"
            f"No further action is required at this time.\n\n"
            f"— PENRO WSTI System"
        )

    elif work_item.review_decision == "revision":
        email_subject = "Action Required: Work Item Needs Revision"
        email_body = (
            f"Good day.\n\n"
            f"Your submitted work item under the work cycle "
            f"“{work_item.workcycle.title}” has been reviewed and requires revision.\n\n"
            f"Please log in to the system to review the remarks and "
            f"resubmit accordingly.\n\n"
            f"— PENRO WSTI System"
        )

    else:
        email_subject = "Notice: Work Item Review Reverted"
        email_body = (
            f"Good day.\n\n"
            f"The review status of your submitted work item under "
            f"“{work_item.workcycle.title}” has been reverted to pending.\n\n"
            f"This notice is issued for your information.\n\n"
            f"— PENRO WSTI System"
        )

    send_mail(
        subject=email_subject,
        message=email_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
