from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt

from accounts.models import (
    WorkItem,
    WorkItemMessage,
    WorkItemReadState,
)


# ============================================================
# WORK ITEM DISCUSSION (ADMIN)
# ============================================================
@login_required
@xframe_options_exempt
def admin_work_item_discussion(request, item_id):
    # --------------------------------------------------------
    # LOAD WORK ITEM
    # --------------------------------------------------------
    work_item = get_object_or_404(
        WorkItem.objects.select_related("owner", "workcycle"),
        id=item_id,
    )

    # --------------------------------------------------------
    # POST MESSAGE (ADMIN → USER)
    # --------------------------------------------------------
    if request.method == "POST":
        text = request.POST.get("message", "").strip()

        if not text:
            messages.warning(request, "Message cannot be empty.")
            return redirect(
                "admin_app:work-item-discussion",
                item_id=work_item.id,
            )

        # Create chat message (do NOT touch read cursor)
        WorkItemMessage.objects.create(
            work_item=work_item,
            sender=request.user,
            message=text,
        )

        # ✅ Flash notification for UI toast
        messages.success(request, "Message sent.")

        # PRG pattern
        return redirect(
            "admin_app:work-item-discussion",
            item_id=work_item.id,
        )

    # --------------------------------------------------------
    # GET REQUEST → MARK THREAD AS READ (ADMIN VIEWING)
    # --------------------------------------------------------
    WorkItemMessage.mark_thread_as_read(
        work_item=work_item,
        reader=request.user,
    )

    # --------------------------------------------------------
    # LOAD MESSAGES
    # --------------------------------------------------------
    messages_qs = (
        work_item.messages
        .select_related("sender")
        .order_by("created_at", "id")
    )

    # --------------------------------------------------------
    # READ CURSOR (FOR READ RECEIPT UI)
    # --------------------------------------------------------
    read_state = (
        WorkItemReadState.objects
        .filter(
            work_item=work_item,
            user=request.user,
        )
        .first()
    )

    last_read_message_id = (
        read_state.last_read_message_id
        if read_state and read_state.last_read_message_id
        else 0
    )

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------
    return render(
        request,
        "admin/page/work_item_discussion.html",
        {
            "work_item": work_item,
            "messages": messages_qs,
            "has_messages": messages_qs.exists(),
            "last_read_message_id": last_read_message_id,
        },
    )
