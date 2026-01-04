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

def submit_work_item(work_item, user):
    """
    Submit completed work item.
    Requires at least one attachment to exist.
    """
    if work_item.status == "done":
        raise ValidationError("This work item has already been submitted.")

    # Check if attachments exist
    has_attachments = WorkItemAttachment.objects.filter(
        work_item=work_item
    ).exists()

    if not has_attachments:
        raise ValidationError(
            "At least one attachment is required before submission. "
            "Please upload Matrix A, Matrix B, or MOV files."
        )

    # Submit the work item
    work_item.status = "done"
    work_item.review_decision = "pending"
    work_item.submitted_at = timezone.now()
    work_item.save(update_fields=[
        "status",
        "review_decision",
        "submitted_at",
    ])


# ============================================================
# ATTACHMENTS (FLEXIBLE UPLOAD)
# ============================================================

def add_attachment_to_work_item(*, work_item, files, attachment_type, user):
    """
    Add attachments to a work item with flexible folder resolution.
    
    Supports:
    - Users with full org assignment (Division > Section > Service > Unit)
    - Users with partial org assignment (Division only, Section only, etc.)
    - Users with NO org assignment (creates "Unassigned" folder)
    
    Folder structure is automatically resolved based on:
    - Year (from work cycle deadline)
    - Attachment type (MATRIX_A, MATRIX_B, MOV)
    - Work cycle name
    - User's organizational assignment (deepest available level)
    
    Args:
        work_item: WorkItem instance
        files: List of uploaded files
        attachment_type: str ("matrix_a", "matrix_b", "mov")
        user: User performing the upload
    
    Raises:
        PermissionDenied: If user lacks upload permission
        ValidationError: If inputs are invalid
    """

    if not user:
        raise PermissionDenied("Uploader is required.")

    if not attachment_type:
        raise ValidationError("Attachment type is required.")

    if not files:
        raise ValidationError("No files provided.")

    # Validate attachment type
    valid_types = {"matrix_a", "matrix_b", "mov"}
    if attachment_type not in valid_types:
        raise ValidationError(
            f"Invalid attachment type '{attachment_type}'. "
            f"Must be one of: {', '.join(valid_types)}"
        )

    # Check if user can upload to this work item
    if user.login_role != "admin" and work_item.owner_id != user.id:
        raise PermissionDenied(
            "You can only upload attachments to your own work items."
        )

    # Check if work item is approved (locked)
    if work_item.review_decision == "approved":
        raise PermissionDenied(
            "Cannot add attachments to approved work items."
        )

    # Create attachments
    # Folder will be auto-resolved in WorkItemAttachment.save()
    # No need to check org assignment here - flexible resolution handles it
    created_count = 0
    
    for file in files:
        try:
            WorkItemAttachment.objects.create(
                work_item=work_item,
                file=file,
                attachment_type=attachment_type,
                uploaded_by=user,
                # folder is None - will be auto-resolved based on:
                # 1. Work item's work cycle
                # 2. Attachment type
                # 3. User's org assignment (or "Unassigned" if none)
            )
            created_count += 1
        except Exception as e:
            # If any file fails, raise error with context
            raise ValidationError(
                f"Failed to upload '{file.name}': {str(e)}"
            )

    return created_count


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


# ============================================================
# HELPER: Check Upload Permission
# ============================================================

def can_user_upload_to_work_item(user, work_item):
    """
    Check if a user has permission to upload attachments to a work item.
    
    Returns:
        tuple: (bool, str) - (can_upload, reason_if_not)
    """
    
    # Admins can upload to any work item
    if user.login_role == "admin":
        return True, None
    
    # Users can only upload to their own work items
    if work_item.owner_id != user.id:
        return False, "You can only upload to your own work items."
    
    # Cannot upload to approved work items
    if work_item.review_decision == "approved":
        return False, "Cannot upload to approved work items."
    
    # Cannot upload to inactive work items
    if not work_item.is_active:
        return False, "Cannot upload to archived work items."
    
    return True, None


# ============================================================
# HELPER: Get Attachment Summary
# ============================================================

def get_attachment_summary(work_item):
    """
    Get summary of attachments for a work item.
    
    Returns:
        dict: {
            "total": int,
            "by_type": {
                "matrix_a": int,
                "matrix_b": int,
                "mov": int,
            },
            "has_all_required": bool,
            "missing_types": list,
        }
    """
    
    attachments = WorkItemAttachment.objects.filter(work_item=work_item)
    
    summary = {
        "total": attachments.count(),
        "by_type": {
            "matrix_a": attachments.filter(attachment_type="matrix_a").count(),
            "matrix_b": attachments.filter(attachment_type="matrix_b").count(),
            "mov": attachments.filter(attachment_type="mov").count(),
        }
    }
    
    # Check if all required types are present
    # Assuming all three types are required
    required_types = {"matrix_a", "matrix_b", "mov"}
    uploaded_types = set(
        attachments.values_list("attachment_type", flat=True).distinct()
    )
    
    missing_types = required_types - uploaded_types
    
    summary["has_all_required"] = len(missing_types) == 0
    summary["missing_types"] = list(missing_types)
    
    return summary


# ============================================================
# HELPER: Validate Work Item Ready for Submission
# ============================================================

def validate_work_item_for_submission(work_item):
    """
    Validate if a work item is ready for submission.
    
    Raises:
        ValidationError: If work item cannot be submitted
    
    Returns:
        dict: Summary of validation checks
    """
    
    errors = []
    
    # Check if already submitted
    if work_item.status == "done":
        errors.append("Work item is already submitted.")
    
    # Check if work item is active
    if not work_item.is_active:
        errors.append("Cannot submit an archived work item.")
    
    # Check if work cycle is still active
    if not work_item.workcycle.is_active:
        errors.append("Cannot submit to an archived work cycle.")
    
    # Check attachments
    attachment_summary = get_attachment_summary(work_item)
    
    if attachment_summary["total"] == 0:
        errors.append("At least one attachment is required.")
    
    # Optional: Check if all required types are present
    if not attachment_summary["has_all_required"]:
        missing = ", ".join(attachment_summary["missing_types"])
        errors.append(f"Missing required attachment types: {missing}")
    
    if errors:
        raise ValidationError(" ".join(errors))
    
    return {
        "valid": True,
        "attachment_summary": attachment_summary,
    }