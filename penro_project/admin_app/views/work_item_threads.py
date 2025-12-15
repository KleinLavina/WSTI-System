from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max
from django.shortcuts import render

from accounts.models import WorkItem


@login_required
def admin_work_item_threads(request):
    """
    List conversation threads for admins.
    Each thread represents a WorkItem.
    """

    work_items = (
        WorkItem.objects
        .select_related("owner", "workcycle")
        .annotate(
            message_count=Count("messages"),
            last_message_at=Max("messages__created_at")
        )
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
