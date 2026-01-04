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

    - Returns REAL WorkItem objects
    - Cursor-based unread counts
    - Safe for multiple admins
    """

    work_items = (
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

    # ----------------------------------------------------
    # ATTACH UNREAD COUNT TO EACH WorkItem (NO DICTS)
    # ----------------------------------------------------
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

    return render(
        request,
        "admin/page/work_item_thread_list.html",
        {
            "work_items": work_items,
        }
    )
