from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.clickjacking import xframe_options_exempt

from accounts.models import WorkItem, WorkItemMessage


# ============================================================
# REVIEW WORK ITEM (ADMIN)
# ============================================================
@xframe_options_exempt
@login_required
def review_work_item(request, item_id):
    """
    Admin review page for a submitted WorkItem.

    - Shows submission details
    - Groups attachments by type
    - Updates review_decision
    - Posts system message to discussion
    - Sends UI notification via Django messages
    """

    work_item = get_object_or_404(
        WorkItem.objects
        .select_related("owner", "workcycle")
        .prefetch_related("attachments", "messages"),
        id=item_id,
        status="done",
    )

    # --------------------------------------------------------
    # HANDLE REVIEW UPDATE
    # --------------------------------------------------------
    if request.method == "POST" and request.POST.get("action") == "update_review":
        decision = request.POST.get("review_decision")

        if decision in {"pending", "approved", "revision"}:
            old_decision = work_item.review_decision
            work_item.review_decision = decision
            work_item.save()  # ensures reviewed_at is updated

            # --------------------------------------------
            # DISCUSSION MESSAGE (PERSISTENT)
            # --------------------------------------------
            if old_decision != decision:
                decision_label = decision.replace("_", " ").title()

                WorkItemMessage.objects.create(
                    work_item=work_item,
                    sender=request.user,
                    sender_role=request.user.login_role,
                    message=(
                        f"📝 Review Update\n\n"
                        f"This work item has been marked as "
                        f"{decision_label}."
                    )
                )

                # ----------------------------------------
                # UI NOTIFICATION (TEMPORARY)
                # ----------------------------------------
                messages.success(
                    request,
                    f"Review decision updated to {decision_label}."
                )
            else:
                messages.info(
                    request,
                    "Review decision was not changed."
                )

        else:
            messages.error(
                request,
                "Invalid review decision submitted."
            )

        return redirect(
            "admin_app:work-item-review",
            item_id=work_item.id
        )

    # --------------------------------------------------------
    # GROUP ATTACHMENTS BY TYPE
    # --------------------------------------------------------
    attachments_by_type = defaultdict(list)

    for attachment in work_item.attachments.all():
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


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils import timezone
from django.db import transaction

from accounts.models import WorkItem, WorkItemMessage


# ============================================================
# WORK ITEM DISCUSSION (ADMIN)
# ============================================================
@login_required
@xframe_options_exempt
def admin_work_item_discussion(request, item_id):
    """
    Admin discussion thread for a WorkItem.
    Used inside modal / iframe.

    Responsibilities:
    - Send messages
    - Prevent empty messages
    - Sender messages start as READ
    - Mark other party's messages as read when opened
    - Provide unread count
    - Allow template to hide UI if no messages exist
    """

    # --------------------------------------------------------
    # LOAD WORK ITEM
    # --------------------------------------------------------
    work_item = get_object_or_404(
        WorkItem.objects.select_related("owner", "workcycle"),
        id=item_id
    )

    # --------------------------------------------------------
    # POST NEW MESSAGE
    # --------------------------------------------------------
    if request.method == "POST":
        text = request.POST.get("message", "").strip()

        if not text:
            messages.warning(request, "Message cannot be empty.")
            return redirect(
                "admin_app:work-item-discussion",
                item_id=work_item.id
            )

        WorkItemMessage.objects.create(
            work_item=work_item,
            sender=request.user,
            sender_role=request.user.login_role,
            message=text,
            is_read=True,                 # Sender has read it
            read_at=timezone.now(),
        )

        messages.success(request, "Message sent.")

        return redirect(
            "admin_app:work-item-discussion",
            item_id=work_item.id
        )

    # --------------------------------------------------------
    # MARK OTHER PARTY'S MESSAGES AS READ (SAFE + CENTRALIZED)
    # --------------------------------------------------------
    with transaction.atomic():
        WorkItemMessage.mark_thread_as_read(
            work_item=work_item,
            reader=request.user
        )

    # --------------------------------------------------------
    # LOAD DISCUSSION
    # --------------------------------------------------------
    messages_qs = (
        work_item.messages
        .select_related("sender")
        .order_by("created_at")
    )

    # --------------------------------------------------------
    # DISCUSSION STATE
    # --------------------------------------------------------
    has_messages = messages_qs.exists()

    unread_count = work_item.messages.filter(
        is_read=False
    ).exclude(
        sender=request.user
    ).count()

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------
    return render(
        request,
        "admin/page/work_item_discussion.html",
        {
            "work_item": work_item,
            "messages": messages_qs,
            "has_messages": has_messages,
            "unread_count": unread_count,
        }
    )
