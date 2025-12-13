from django.utils import timezone
from django.core.exceptions import ValidationError

from accounts.models import WorkItem, WorkItemAttachment


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


def submit_work_item(work_item, files=None, message=None, user=None):
    """
    Submit completed work item.
    """
    if work_item.status == "done":
        raise ValidationError("This work item has already been submitted.")

    if files is None or len(files) == 0:
        raise ValidationError("At least one attachment is required.")

    # Save attachments
    for f in files:
        WorkItemAttachment.objects.create(
            work_item=work_item,
            file=f,
            uploaded_by=user
        )

    # Save submission
    work_item.status = "done"
    work_item.review_decision = "pending"
    work_item.submitted_at = timezone.now()

    if message:
        work_item.message = message

    work_item.save()

from accounts.models import WorkItemAttachment


def add_attachment_to_work_item(work_item, files, user):
    """
    Allow adding attachments even after submission.
    """
    if not files:
        raise ValueError("No files provided.")

    for f in files:
        WorkItemAttachment.objects.create(
            work_item=work_item,
            file=f,
            uploaded_by=user
        )
        
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
