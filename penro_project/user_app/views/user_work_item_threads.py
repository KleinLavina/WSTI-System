from django.db.models import Count, Max
from accounts.models import WorkItem, WorkItemMessage
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

@login_required
def user_work_item_threads(request):
    work_items = (
        WorkItem.objects
        .filter(owner=request.user, is_active=True)
        .annotate(
            message_count=Count("messages"),
            last_message_at=Max("messages__created_at")
        )
        .select_related("workcycle")
        .order_by("-last_message_at", "workcycle__due_at")
    )

    return render(
        request,
        "user/page/work_item_thread_list.html",
        {
            "work_items": work_items,
        }
    )
