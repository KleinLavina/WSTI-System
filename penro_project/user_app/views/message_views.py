from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils import timezone
from django.db import transaction

from accounts.models import WorkItem, WorkItemMessage


# ============================================================
# WORK ITEM DISCUSSION (USER)
# ============================================================
@login_required
@xframe_options_exempt
def user_work_item_discussion(request, item_id):
    """
    User discussion thread for a WorkItem.
    Used inside modal / iframe.

    Responsibilities:
    - Send messages
    - Prevent empty messages
    - Sender messages start as READ
    - Mark admin messages as read when opened
    - Load discussion messages in order
    """

    # --------------------------------------------------------
    # LOAD WORK ITEM (USER SCOPE)
    # --------------------------------------------------------
    work_item = get_object_or_404(
        WorkItem.objects.select_related("owner", "workcycle"),
        id=item_id,
        owner=request.user,     # 🔐 important: user can only see their own
    )

    # --------------------------------------------------------
    # POST NEW MESSAGE
    # --------------------------------------------------------
    if request.method == "POST":
        text = request.POST.get("message", "").strip()

        if not text:
            messages.warning(request, "Message cannot be empty.")
            return redirect(
                "user_app:work-item-discussion",
                item_id=work_item.id
            )

        WorkItemMessage.objects.create(
            work_item=work_item,
            sender=request.user,
            sender_role=request.user.login_role,
            message=text,
            is_read=True,                 # sender already read it
            read_at=timezone.now(),
        )

        messages.success(request, "Message sent.")

        return redirect(
            "user_app:work-item-discussion",
            item_id=work_item.id
        )

    # --------------------------------------------------------
    # MARK ADMIN MESSAGES AS READ (SAFE + CENTRALIZED)
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
    # RENDER
    # --------------------------------------------------------
    return render(
        request,
        "user/page/work_item_discussion.html",
        {
            "work_item": work_item,
            "messages": messages_qs,
        }
    )
