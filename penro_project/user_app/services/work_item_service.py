from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied

from accounts.models import WorkItemAttachment


# ============================================================
# STATUS UPDATES
# ============================================================

def update_work_item_status(work_item, new_status):
    """
    Allow user to toggle only between not_started and working_on_it
    """
    if work_item.status == "done":
        raise ValidationError("Completed work items cannot be modified.")

    if new_status not in ["not_started", "working_on_it"]:
        raise ValidationError("Invalid status change.")

    work_item.status = new_status
    work_item.save(update_fields=["status"])


# ============================================================
# SUBMISSION
# ============================================================

def submit_work_item(work_item, files=None, message=None, user=None):
    """
    Submit completed work item.
    Allows submission if attachments already exist.
    """
    if work_item.status == "done":
        raise ValidationError("This work item has already been submitted.")

    has_existing_attachments = WorkItemAttachment.objects.filter(
        work_item=work_item
    ).exists()

    if (not files or len(files) == 0) and not has_existing_attachments:
        raise ValidationError("At least one attachment is required.")

    if files:
        for f in files:
            WorkItemAttachment.objects.create(
                work_item=work_item,
                file=f,
                uploaded_by=user
            )

    work_item.status = "done"
    work_item.review_decision = "pending"
    work_item.submitted_at = timezone.now()

    if message:
        work_item.message = message

    work_item.save(update_fields=[
        "status",
        "review_decision",
        "submitted_at",
        "message",
    ])


# ============================================================
# ATTACHMENTS (🔥 FIXED)
# ============================================================

def add_attachment_to_work_item(*, work_item, files, attachment_type, user):
    """
    Allow adding attachments even after submission.
    Each attachment MUST have a type.
    """

    if not user:
        raise PermissionDenied("Uploader is required.")

    # ✅ FIX: use canonical org accessor
    org = user.primary_org
    if not org:
        raise PermissionDenied(
            "You are not assigned to any organization. "
            "Please contact an administrator."
        )

    if not attachment_type:
        raise ValidationError("Attachment type is required.")

    if not files:
        raise ValidationError("No files provided.")

    for f in files:
        WorkItemAttachment.objects.create(
            work_item=work_item,
            file=f,
            attachment_type=attachment_type,
            uploaded_by=user
        )


# ============================================================
# CONTEXT UPDATES
# ============================================================

def update_work_item_context(work_item, label=None, message=None):
    """
    Update contextual fields WITHOUT changing submission or status.
    Allowed even after submission.
    """
    if label is not None:
        work_item.status_label = label

    if message is not None:
        work_item.message = message

    work_item.save(update_fields=["status_label", "message"])
