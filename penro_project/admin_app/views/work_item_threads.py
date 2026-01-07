from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max
from django.shortcuts import render

from accounts.models import (
    WorkItem,
    WorkItemReadState,
)


@login_required
def admin_work_item_threads(request):
    """
    Admin inbox view for WorkItem conversations.

    Ordering rules:
    1. Threads with unread messages first
    2. Newest activity first within each group
    """

    # --------------------------------------------------
    # BASE QUERYSET (ONLY THREADS WITH MESSAGES)
    # --------------------------------------------------
    work_items = list(
        WorkItem.objects
        .select_related("owner", "workcycle")
        .prefetch_related("messages", "read_states")
        .annotate(
            message_count=Count("messages", distinct=True),
            last_message_at=Max("messages__created_at"),
        )
        .filter(message_count__gt=0)
        .order_by("-last_message_at", "-submitted_at")
    )

    # --------------------------------------------------
    # ATTACH UNREAD COUNT (PER ADMIN)
    # --------------------------------------------------
    for item in work_items:
        read_state = next(
            (
                rs for rs in item.read_states.all()
                if rs.user_id == request.user.id
            ),
            None,
        )

        last_read_id = read_state.last_read_message_id if read_state else 0

        item.unread_count = (
            item.messages
            .filter(id__gt=last_read_id)
            .exclude(sender=request.user)
            .count()
        )

    # --------------------------------------------------
    # FINAL INBOX SORT
    # --------------------------------------------------
    # unread first → newest first
    work_items.sort(
        key=lambda item: (
            item.unread_count == 0,   # False (unread) comes first
            -(item.last_message_at.timestamp() if item.last_message_at else 0),
        )
    )

    return render(
        request,
        "admin/page/work_item_thread_list.html",
        {
            "work_items": work_items,
            "total_active_threads": len(work_items),
        }
    )
