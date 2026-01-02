from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.shortcuts import render

from accounts.models import WorkItem


@login_required
def user_work_item_threads(request):
    """
    User inbox view for WorkItem conversations.

    Guarantees:
    - Only ACTIVE work items owned by the user
    - Only work items WITH messages appear
    - Only UNREAD messages from ADMIN are counted
    - Correct ordering by last message activity
    - No duplicate rows or inflated counts
    """

    work_items = (
        WorkItem.objects
        # ----------------------------------------------------
        # USER SCOPE
        # ----------------------------------------------------
        .filter(
            owner=request.user,
            is_active=True
        )

        # ----------------------------------------------------
        # BASIC RELATION OPTIMIZATION
        # ----------------------------------------------------
        .select_related("workcycle")

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
        # UNREAD COUNT (ADMIN ONLY)
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
            "workcycle__due_at"
        )
    )

    return render(
        request,
        "user/page/work_item_thread_list.html",
        {
            "work_items": work_items,
        }
    )
