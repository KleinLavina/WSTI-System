from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.shortcuts import render

from accounts.models import WorkItem


@login_required
def admin_work_item_threads(request):
    """
    Admin inbox view for WorkItem conversations.

    Guarantees:
    - Only work items WITH messages appear
    - Only UNREAD messages from the other party are counted
    - Unread count disappears when messages are read
    - No duplicate rows or inflated counts
    - Ordered by most recent message activity
    """

    work_items = (
        WorkItem.objects
        # ----------------------------------------------------
        # BASIC RELATION OPTIMIZATION
        # ----------------------------------------------------
        .select_related("owner", "workcycle")

        # ----------------------------------------------------
        # REQUIRE AT LEAST ONE MESSAGE
        # ----------------------------------------------------
        .annotate(
            has_messages=Count(
                "messages",
                distinct=True
            )
        )
        .filter(has_messages__gt=0)

        # ----------------------------------------------------
        # UNREAD COUNT (OTHER PARTY ONLY)
        # ----------------------------------------------------
        .annotate(
            unread_count=Count(
                "messages",
                filter=Q(
                    messages__is_read=False
                ) & ~Q(
                    messages__sender=request.user
                ),
                distinct=True,
            )
        )

        # ----------------------------------------------------
        # LAST MESSAGE TIMESTAMP
        # ----------------------------------------------------
        .annotate(
            last_message_at=Max("messages__created_at")
        )

        # ----------------------------------------------------
        # ORDER BY RECENT ACTIVITY
        # ----------------------------------------------------
        .order_by(
            "-last_message_at",
            "-submitted_at"
        )
    )

    return render(
        request,
        "admin/page/work_item_thread_list.html",
        {
            "work_items": work_items,
        }
    )
