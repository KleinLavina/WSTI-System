# user_app/views/message_views.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q, Max
from django.http import JsonResponse
from datetime import timedelta

from accounts.models import (
    WorkItem,
    WorkItemMessage,
    WorkItemReadState,
    WorkCycle,
)



# ============================================================
# DISCUSSIONS LIST (USER)
# ============================================================
@login_required
def user_discussions_list(request):
    work_items = (
        WorkItem.objects
        .filter(owner=request.user, is_active=True)
        .select_related("workcycle", "workcycle__created_by")
        .prefetch_related("messages", "read_states")
    )

    results = []
    total_unread = 0

    for item in work_items:
        read_state = next(
            (rs for rs in item.read_states.all() if rs.user_id == request.user.id),
            None
        )

        last_read_id = read_state.last_read_message_id if read_state else 0

        unread_count = (
            item.messages
            .filter(id__gt=last_read_id)
            .exclude(sender=request.user)
            .count()
        )

        total_unread += unread_count

        results.append({
            "work_item": item,
            "unread_count": unread_count,
            "last_message_at": item.messages.last().created_at if item.messages.exists() else None,
            "total_message_count": item.messages.count(),
        })

    return render(
        request,
        "user/page/discussions_list.html",
        {
            "work_items": results,
            "total_unread": total_unread,
        }
    )

# ============================================================
# WORK ITEM DISCUSSION (USER)
# ============================================================
@login_required
@xframe_options_exempt
def user_work_item_discussion(request, item_id):
    work_item = get_object_or_404(
        WorkItem.objects.select_related("owner", "workcycle"),
        id=item_id,
        owner=request.user,
    )

    # -----------------------------
    # POST MESSAGE
    # -----------------------------
    if request.method == "POST":
        text = request.POST.get("message", "").strip()

        if not text:
            messages.warning(request, "Message cannot be empty.")
            return redirect("user_app:work-item-discussion", item_id=work_item.id)

        WorkItemMessage.objects.create(
            work_item=work_item,
            sender=request.user,
            message=text,
        )

        return redirect("user_app:work-item-discussion", item_id=work_item.id)

    # -----------------------------
    # MARK THREAD AS READ (CORRECT)
    # -----------------------------
    WorkItemMessage.mark_thread_as_read(
        work_item=work_item,
        reader=request.user
    )

    messages_qs = (
        work_item.messages
        .select_related("sender")
        .order_by("created_at", "id")
    )

    return render(
        request,
        "user/page/work_item_discussion.html",
        {
            "work_item": work_item,
            "messages": messages_qs,
            "has_messages": messages_qs.exists(),
        }
    )

# ============================================================
# MARK ALL AS READ (BULK ACTION)
# ============================================================
@login_required
def user_mark_all_discussions_read(request):
    if request.method == "POST":
        now = timezone.now()

        for item in WorkItem.objects.filter(owner=request.user, is_active=True):
            last_msg = (
                item.messages
                .exclude(sender=request.user)
                .order_by("-id")
                .first()
            )

            if last_msg:
                WorkItemReadState.objects.update_or_create(
                    work_item=item,
                    user=request.user,
                    defaults={
                        "last_read_message": last_msg,
                        "last_read_at": now,
                    }
                )

        messages.success(request, "All discussions marked as read.")

    return redirect("user_app:discussions-list")

# ============================================================
# GET DISCUSSION STATS (API ENDPOINT)
# ============================================================
@login_required
def user_discussion_stats(request):
    total_unread = 0
    active_conversations = 0

    work_items = (
        WorkItem.objects
        .filter(owner=request.user, is_active=True)
        .prefetch_related("messages", "read_states")
    )

    recent_cutoff = timezone.now() - timedelta(days=7)

    for item in work_items:
        read_state = next(
            (rs for rs in item.read_states.all() if rs.user_id == request.user.id),
            None
        )

        last_read_id = read_state.last_read_message_id if read_state else 0

        unread = (
            item.messages
            .filter(id__gt=last_read_id)
            .exclude(sender=request.user)
            .count()
        )

        total_unread += unread

        if item.messages.filter(created_at__gte=recent_cutoff).exists():
            active_conversations += 1

    conversations_by_status = {}
    for state in WorkCycle.LifecycleState:
        conversations_by_status[state.label] = sum(
            1 for item in work_items
            if item.workcycle.lifecycle_state == state.value
        )

    return JsonResponse({
        "total_conversations": work_items.count(),
        "total_unread": total_unread,
        "active_conversations": active_conversations,
        "conversations_by_status": conversations_by_status,
    })

# ============================================================
# UTILITY: Get Unread Count for Navigation Badge
# ============================================================
def get_user_total_unread_count(user):
    total = 0

    items = (
        WorkItem.objects
        .filter(owner=user, is_active=True)
        .prefetch_related("messages", "read_states")
    )

    for item in items:
        read_state = next(
            (rs for rs in item.read_states.all() if rs.user_id == user.id),
            None
        )

        last_read_id = read_state.last_read_message_id if read_state else 0

        total += (
            item.messages
            .filter(id__gt=last_read_id)
            .exclude(sender=user)
            .count()
        )

    return total
