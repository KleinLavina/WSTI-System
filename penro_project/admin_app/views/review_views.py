from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.clickjacking import xframe_options_exempt

from accounts.models import WorkItem, WorkItemMessage


# ============================================================
# REVIEW WORK ITEM (ADMIN)
# ============================================================
@xframe_options_exempt
def review_work_item(request, item_id):
    """
    Admin review page for a submitted WorkItem.

    - Shows submission details
    - Groups attachments by type (Matrix A, Matrix B, MOV)
    - Allows updating review_decision
    - Correctly records reviewed_at via model save()
    """

    work_item = get_object_or_404(
        WorkItem.objects
        .select_related("owner", "workcycle")
        .prefetch_related("attachments"),
        id=item_id,
        status="done",  # only submitted items can be reviewed
    )

    # --------------------------------------------------------
    # HANDLE REVIEW UPDATE
    # --------------------------------------------------------
    if request.method == "POST" and request.POST.get("action") == "update_review":
        decision = request.POST.get("review_decision")

        if decision in {"pending", "approved", "revision"}:
            work_item.review_decision = decision

            # IMPORTANT:
            # Do NOT use update_fields here
            # so reviewed_at is saved correctly
            work_item.save()

        return redirect(
            "admin_app:work-item-review",
            item_id=work_item.id
        )

    # --------------------------------------------------------
    # GROUP ATTACHMENTS BY TYPE
    # --------------------------------------------------------
    attachments_by_type = defaultdict(list)

    for attachment in work_item.attachments.all():
        # Uses Django choice label: "Matrix A", "Matrix B", "MOV"
        label = attachment.get_attachment_type_display()
        attachments_by_type[label].append(attachment)

    return render(
        request,
        "admin/page/review_work_item.html",
        {
            "work_item": work_item,
            "attachments_by_type": dict(attachments_by_type),
        }
    )


# ============================================================
# WORK ITEM DISCUSSION (ADMIN)
# ============================================================
@login_required
@xframe_options_exempt
def admin_work_item_discussion(request, item_id):
    """
    Admin discussion thread for a WorkItem.
    Used inside modal / iframe.
    """

    work_item = get_object_or_404(
        WorkItem.objects.select_related("owner", "workcycle"),
        id=item_id
    )

    # --------------------------------------------------------
    # POST NEW MESSAGE
    # --------------------------------------------------------
    if request.method == "POST":
        text = request.POST.get("message", "").strip()

        if text:
            WorkItemMessage.objects.create(
                work_item=work_item,
                sender=request.user,
                sender_role=request.user.login_role,
                message=text
            )

        return redirect(
            "admin_app:work-item-discussion",
            item_id=work_item.id
        )

    # --------------------------------------------------------
    # LOAD DISCUSSION
    # --------------------------------------------------------
    messages_qs = (
        work_item.messages
        .select_related("sender")
        .order_by("created_at")
    )

    return render(
        request,
        "admin/page/work_item_discussion.html",
        {
            "work_item": work_item,
            "messages": messages_qs,
        }
    )
