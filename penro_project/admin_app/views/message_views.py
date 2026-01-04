from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_exempt

from accounts.models import WorkItem, WorkItemMessage
from notifications.services.review import notify_work_item_review_changed

@login_required
@xframe_options_exempt
def admin_work_item_discussion(request, item_id):
    """
    Admin discussion thread for a WorkItem.

    Responsibilities:
    - Send messages
    - Prevent empty messages
    - Sender messages start as READ
    - Mark other party's messages as read
    - Provide unread count
    """

    # --------------------------------------------------------
    # LOAD WORK ITEM
    # --------------------------------------------------------
    work_item = get_object_or_404(
        WorkItem.objects.select_related("owner", "workcycle"),
        id=item_id,
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
                item_id=work_item.id,
            )

        WorkItemMessage.objects.create(
            work_item=work_item,
            sender=request.user,
            sender_role=request.user.login_role,
            message=text,
            is_read=True,
            read_at=timezone.now(),
        )

        messages.success(request, "Message sent.")

        return redirect(
            "admin_app:work-item-discussion",
            item_id=work_item.id,
        )

    # --------------------------------------------------------
    # MARK USER MESSAGES AS READ (ATOMIC)
    # --------------------------------------------------------
    with transaction.atomic():
        WorkItemMessage.mark_thread_as_read(
            work_item=work_item,
            reader=request.user,
        )

    # --------------------------------------------------------
    # LOAD DISCUSSION
    # --------------------------------------------------------
    messages_qs = (
        work_item.messages
        .select_related("sender")
        .order_by("created_at")
    )

    unread_count = (
        work_item.messages
        .filter(is_read=False)
        .exclude(sender=request.user)
        .count()
    )

    return render(
        request,
        "admin/page/work_item_discussion.html",
        {
            "work_item": work_item,
            "messages": messages_qs,
            "has_messages": messages_qs.exists(),
            "unread_count": unread_count,
        },
    )