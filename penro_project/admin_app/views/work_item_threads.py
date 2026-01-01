from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.shortcuts import render

from accounts.models import WorkItem


@login_required
def admin_work_item_threads(request):
    """
    List conversation threads for admins.
    Each thread represents a WorkItem.

    Rules:
    - Show ONLY work items that have messages
    - Show ONLY unread message count
    - Unread count disappears when everything is read
    """

    work_items = (
        WorkItem.objects
        .select_related("owner", "workcycle")

        # ----------------------------------------------------
        # ONLY WORK ITEMS THAT HAVE AT LEAST ONE MESSAGE
        # ----------------------------------------------------
        .filter(messages__isnull=False)
        .distinct()

        # ----------------------------------------------------
        # UNREAD COUNT (not read AND not sent by admin)
        # ----------------------------------------------------
        .annotate(
            unread_count=Count(
                "messages",
                filter=Q(
                    messages__is_read=False
                ) & ~Q(
                    messages__sender=request.user
                ),
                distinct=True
            )
        )

        # ----------------------------------------------------
        # LAST MESSAGE TIMESTAMP
        # ----------------------------------------------------
        .annotate(
            last_message_at=Max("messages__created_at")
        )

        # ----------------------------------------------------
        # ORDER BY ACTIVITY
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
