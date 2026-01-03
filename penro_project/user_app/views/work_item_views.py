from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from accounts.models import WorkItem, WorkItemMessage, WorkItemAttachment
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from ..services.work_item_service import (
    update_work_item_status,
    submit_work_item,
    add_attachment_to_work_item,
    update_work_item_context,
)
from notifications.services.status import notify_work_item_status_changed

# ============================================================
# HELPER: Calculate Time Remaining
# ============================================================
# ============================================================
# TIME REMAINING LOGIC (STATUS-AWARE)
# ============================================================
# ============================================================
# TIME REMAINING LOGIC (STATUS-AWARE)
# ============================================================
def calculate_time_remaining(due_at, status, submitted_at=None):
    """
    Human-readable time logic based on:
    - deadline
    - submission timestamp

    RULES:
    1. Not submitted → live countdown
    2. Submitted → frozen at submitted_at
    """

    now = timezone.now()

    # -------------------------------------------------
    # NOT SUBMITTED → LIVE COUNTDOWN
    # -------------------------------------------------
    if status != "done" or not submitted_at:
        delta = due_at - now

        if delta.total_seconds() >= 0:
            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60

            if days > 0:
                return f"{days}d remaining"
            elif hours > 0:
                return f"{hours}h remaining"
            else:
                return f"{minutes}m remaining"

        # overdue & not submitted
        overdue = abs(delta)
        days = overdue.days
        hours = overdue.seconds // 3600
        minutes = (overdue.seconds % 3600) // 60

        if days > 0:
            return f"{days}d {hours}h overdue"
        elif hours > 0:
            return f"{hours}h {minutes}m overdue"
        else:
            return f"{minutes}m overdue"

    # -------------------------------------------------
    # SUBMITTED → FROZEN TIME
    # -------------------------------------------------
    delta = due_at - submitted_at

    if delta.total_seconds() >= 0:
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60

        if days > 0:
            return f"Submitted {days}d early"
        elif hours > 0:
            return f"Submitted {hours}h early"
        else:
            return f"Submitted {minutes}m early"

    # submitted late
    late = abs(delta)
    days = late.days
    hours = late.seconds // 3600
    minutes = (late.seconds % 3600) // 60

    if days > 0:
        return f"Submitted {days}d {hours}h late"
    elif hours > 0:
        return f"Submitted {hours}h {minutes}m late"
    else:
        return f"Submitted {minutes}m late"

def get_submission_indicator(due_at, submitted_at):
    """
    Returns:
    - submission_status: 'on_time' | 'late' | None
    - submission_delta: human-readable string
    """

    if not submitted_at:
        return None, None

    delta = due_at - submitted_at
    seconds = abs(int(delta.total_seconds()))

    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60

    if days > 0:
        diff = f"{days}d {hours}h"
    elif hours > 0:
        diff = f"{hours}h {minutes}m"
    else:
        diff = f"{minutes}m"

    if delta.total_seconds() >= 0:
        return "on_time", diff
    else:
        return "late", diff


# ============================================================
# ACTIVE WORK ITEMS (WITH FILTER COUNTS & TIME REMAINING)
# ============================================================
@login_required
def user_work_items(request):
    """
    List ACTIVE work items with:
    - search
    - work item filters (status, review)
    - work cycle lifecycle filters (derived)
    - due date sorting
    - total active count
    - filter counts
    - status-aware time remaining
    """

    now = timezone.now()
    soon_threshold = now + timedelta(days=3)

    # -------------------------------------------------
    # BASE QUERYSET (ACTIVE ONLY)
    # -------------------------------------------------
    base_qs = (
        WorkItem.objects
        .select_related("workcycle")
        .filter(
            owner=request.user,
            is_active=True,
            workcycle__is_active=True
        )
    )

    qs = base_qs

    # -------------------------------------------------
    # SEARCH
    # -------------------------------------------------
    search = request.GET.get("q", "").strip()
    if search:
        qs = qs.filter(
            Q(workcycle__title__icontains=search) |
            Q(message__icontains=search)
        )

    # -------------------------------------------------
    # WORK ITEM FILTERS
    # -------------------------------------------------
    status = request.GET.get("status")
    if status in {"not_started", "working_on_it", "done"}:
        qs = qs.filter(status=status)

    review = request.GET.get("review")
    if review in {"pending", "approved", "revision"}:
        qs = qs.filter(review_decision=review)

    # -------------------------------------------------
    # WORK CYCLE LIFECYCLE FILTER
    # -------------------------------------------------
    lifecycle = request.GET.get("lifecycle")

    if lifecycle == "ongoing":
        qs = qs.filter(workcycle__due_at__gt=soon_threshold)

    elif lifecycle == "due_soon":
        qs = qs.filter(
            workcycle__due_at__gt=now,
            workcycle__due_at__lte=soon_threshold
        )

    elif lifecycle == "lapsed":
        qs = qs.filter(workcycle__due_at__lte=now)

    # -------------------------------------------------
    # FILTER COUNTS (FROM BASE)
    # -------------------------------------------------
    count_base = base_qs
    if search:
        count_base = count_base.filter(
            Q(workcycle__title__icontains=search) |
            Q(message__icontains=search)
        )

    status_counts = {
        "not_started": count_base.filter(status="not_started").count(),
        "working_on_it": count_base.filter(status="working_on_it").count(),
        "done": count_base.filter(status="done").count(),
    }

    review_counts = {
        "pending": count_base.filter(review_decision="pending").count(),
        "approved": count_base.filter(review_decision="approved").count(),
        "revision": count_base.filter(review_decision="revision").count(),
    }

    lifecycle_counts = {
        "ongoing": count_base.filter(workcycle__due_at__gt=soon_threshold).count(),
        "due_soon": count_base.filter(
            workcycle__due_at__gt=now,
            workcycle__due_at__lte=soon_threshold
        ).count(),
        "lapsed": count_base.filter(workcycle__due_at__lte=now).count(),
    }

    # -------------------------------------------------
    # SORTING
    # -------------------------------------------------
    sort = request.GET.get("sort")

    if sort == "due_asc":
        qs = qs.order_by("workcycle__due_at")
    elif sort == "due_desc":
        qs = qs.order_by("-workcycle__due_at")
    else:
        qs = qs.order_by("workcycle__due_at")

    # -------------------------------------------------
    # APPLY TIME REMAINING
    # -------------------------------------------------
    work_items_list = list(qs)
    for item in work_items_list:
        item.time_remaining = calculate_time_remaining(
            due_at=item.workcycle.due_at,
            status=item.status,
            submitted_at=item.submitted_at
        )


    total_active_count = base_qs.count()

    return render(
        request,
        "user/page/work_items.html",
        {
            "work_items": work_items_list,
            "search_query": search,
            "active_status": status,
            "active_review": review,
            "active_lifecycle": lifecycle,
            "active_sort": sort,
            "total_active_count": total_active_count,
            "status_counts": status_counts,
            "review_counts": review_counts,
            "lifecycle_counts": lifecycle_counts,
            "view_mode": "active",
        }
    )


# ============================================================
# WORK ITEM DETAIL
# ============================================================
@login_required
def user_work_item_detail(request, item_id):
    work_item = get_object_or_404(
        WorkItem,
        id=item_id,
        owner=request.user,
        is_active=True
    )

    # -------------------------------------------------
    # TIME REMAINING (FROZEN IF SUBMITTED)
    # -------------------------------------------------
    work_item.time_remaining = calculate_time_remaining(
        due_at=work_item.workcycle.due_at,
        status=work_item.status,
        submitted_at=work_item.submitted_at
    )

    # -------------------------------------------------
    # SUBMISSION STATUS (ON TIME / LATE)
    # -------------------------------------------------
    submission_status, submission_delta = get_submission_indicator(
        due_at=work_item.workcycle.due_at,
        submitted_at=work_item.submitted_at
    )

    # -------------------------------------------------
    # HANDLE ACTIONS
    # -------------------------------------------------
    if request.method == "POST":
        action = request.POST.get("action")

        try:
            # 🔥 Capture old status BEFORE any mutation
            old_status = work_item.status

            if action == "update_status":
                update_work_item_status(
                    work_item,
                    request.POST.get("status")
                )

                notify_work_item_status_changed(
                    work_item=work_item,
                    actor=request.user,
                    old_status=old_status,
                )

                messages.success(request, "Status updated.")

            elif action == "update_context":
                update_work_item_context(
                    work_item=work_item,
                    label=request.POST.get("status_label", "").strip(),
                    message=request.POST.get("message", "").strip(),
                )
                messages.success(request, "Notes updated.")

            elif action == "submit":
                submit_work_item(
                    work_item=work_item,
                    user=request.user
                )

                notify_work_item_status_changed(
                    work_item=work_item,
                    actor=request.user,
                    old_status=old_status,
                )

                messages.success(request, "Work item submitted successfully.")

            elif action == "undo_submit":
                if (
                    work_item.status == "done"
                    and work_item.review_decision == "pending"
                ):
                    # ✅ IMPORTANT FIX:
                    # Do NOT use update_fields — allow model logic to clear submitted_at
                    work_item.status = "working_on_it"
                    work_item.save()

                    notify_work_item_status_changed(
                        work_item=work_item,
                        actor=request.user,
                        old_status=old_status,
                    )

                    messages.info(request, "Submission reverted.")
                else:
                    messages.error(request, "Cannot undo after review.")

            return redirect(
                "user_app:work-item-detail",
                item_id=work_item.id
            )

        except Exception as e:
            messages.error(request, str(e))

    # -------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------
    attachments = work_item.attachments.all()

    attachment_types = [
        ("matrix_a", "Monthly Report Form – Matrix A"),
        ("matrix_b", "Monthly Report Form – Matrix B"),
        ("mov", "Means of Verification (MOV)"),
    ]

    uploaded_types = set(
        work_item.attachments.values_list("attachment_type", flat=True)
    )

    # -------------------------------------------------
    # RENDER
    # -------------------------------------------------
    return render(
        request,
        "user/page/work_item_detail.html",
        {
            "work_item": work_item,
            "attachments": attachments,
            "can_edit": work_item.status != "done",
            "status_choices": WorkItem._meta.get_field("status").choices,
            "attachment_types": attachment_types,
            "uploaded_types": uploaded_types,

            # ✅ submission metadata for UI
            "submission_status": submission_status,
            "submission_delta": submission_delta,
        }
    )
# ============================================================
# INACTIVE WORK ITEMS (WITH FILTER COUNTS)
# ============================================================
@login_required
def user_inactive_work_items(request):
    """
    List INACTIVE (archived) work items with:
    - search
    - work status filter
    - review status filter
    - sorting
    - filter counts
    """

    # -------------------------------------------------
    # BASE QUERYSET (ARCHIVED ONLY)
    # -------------------------------------------------
    base_qs = (
        WorkItem.objects
        .select_related("workcycle")
        .filter(
            owner=request.user,
            is_active=False,  # Archived work items only
        )
    )

    qs = base_qs

    # -------------------------------------------------
    # SEARCH
    # -------------------------------------------------
    search = request.GET.get("q", "").strip()
    if search:
        qs = qs.filter(
            Q(workcycle__title__icontains=search) |
            Q(message__icontains=search) |
            Q(inactive_note__icontains=search)
        )

    # -------------------------------------------------
    # WORK ITEM FILTERS (NO LIFECYCLE)
    # -------------------------------------------------
    status = request.GET.get("status")
    if status in {"not_started", "working_on_it", "done"}:
        qs = qs.filter(status=status)

    review = request.GET.get("review")
    if review in {"pending", "approved", "revision"}:
        qs = qs.filter(review_decision=review)

    # -------------------------------------------------
    # FILTER COUNTS (FROM ARCHIVED BASE)
    # -------------------------------------------------
    count_base = base_qs
    if search:
        count_base = count_base.filter(
            Q(workcycle__title__icontains=search) |
            Q(message__icontains=search) |
            Q(inactive_note__icontains=search)
        )

    status_counts = {
        "not_started": count_base.filter(status="not_started").count(),
        "working_on_it": count_base.filter(status="working_on_it").count(),
        "done": count_base.filter(status="done").count(),
    }

    review_counts = {
        "pending": count_base.filter(review_decision="pending").count(),
        "approved": count_base.filter(review_decision="approved").count(),
        "revision": count_base.filter(review_decision="revision").count(),
    }

    # -------------------------------------------------
    # ARCHIVED ITEMS → NO TIME REMAINING
    # -------------------------------------------------
    work_items_list = list(qs)
    for item in work_items_list:
        item.time_remaining = None  # Explicitly disabled

    # -------------------------------------------------
    # SORTING (ARCHIVE-CENTRIC)
    # -------------------------------------------------
    sort = request.GET.get("sort")

    if sort == "due_asc":
        work_items_list.sort(key=lambda x: x.workcycle.due_at)
    elif sort == "due_desc":
        work_items_list.sort(key=lambda x: x.workcycle.due_at, reverse=True)
    else:
        # Default: most recently archived first
        work_items_list.sort(key=lambda x: x.inactive_at or x.created_at, reverse=True)

    # -------------------------------------------------
    # RENDER
    # -------------------------------------------------
    return render(
        request,
        "user/page/work_items_inactive.html",
        {
            "work_items": work_items_list,
            "search_query": search,
            "active_status": status,
            "active_review": review,
            "active_sort": sort,
            "status_counts": status_counts,
            "review_counts": review_counts,
            "view_mode": "archived",
        }
    )


# ============================================================
# DELETE ATTACHMENT
# ============================================================
@login_required
def delete_work_item_attachment(request, attachment_id):
    attachment = get_object_or_404(
        WorkItemAttachment.objects.select_related("work_item"),
        id=attachment_id,
        work_item__owner=request.user
    )

    work_item = attachment.work_item
    attachment_type = attachment.attachment_type

    # 🔒 Safety rules
    if work_item.review_decision == "approved":
        messages.error(request, "Approved work items cannot be modified.")
        return redirect(
            f"{reverse('user_app:work-item-attachments', args=[work_item.id])}?type={attachment_type}"
        )

    if request.method == "POST":
        attachment.file.delete(save=False)
        attachment.delete()
        messages.success(request, "Attachment deleted.")

    return redirect(
        f"{reverse('user_app:work-item-attachments', args=[work_item.id])}?type={attachment_type}"
    )


# ============================================================
# WORK ITEM ATTACHMENTS
# ============================================================
@login_required
def user_work_item_attachments(request, item_id):
    work_item = get_object_or_404(
        WorkItem,
        id=item_id,
        owner=request.user
    )

    attachment_type = request.GET.get("type")

    TYPE_MAP = {
        "matrix_a": "Monthly Report Form – Matrix A",
        "matrix_b": "Monthly Report Form – Matrix B",
        "mov": "Means of Verification (MOV)",
    }

    if attachment_type not in TYPE_MAP:
        messages.error(request, "Invalid attachment type.")
        return redirect(
            "user_app:work-item-detail",
            item_id=work_item.id
        )

    # ================= UPLOAD =================
    if request.method == "POST":
        try:
            files = request.FILES.getlist("attachments")

            add_attachment_to_work_item(
                work_item=work_item,
                files=files,
                attachment_type=attachment_type,
                user=request.user
            )

            messages.success(request, "Attachment uploaded.")
            return redirect(f"{request.path}?type={attachment_type}")

        except Exception as e:
            messages.error(request, str(e))

    # ================= FETCH ATTACHMENTS =================
    attachments = (
        work_item.attachments
        .filter(attachment_type=attachment_type)
        .order_by("uploaded_at")
    )

    return render(
        request,
        "user/page/work_item_attachments.html",
        {
            "work_item": work_item,
            "attachments": attachments,
            "attachment_type": attachment_type,
            "attachment_label": TYPE_MAP[attachment_type],
        }
    )


# ============================================================
# WORK ITEM COMMENTS
# ============================================================
@login_required
def user_work_item_comments(request, item_id):
    work_item = get_object_or_404(
        WorkItem,
        id=item_id,
        owner=request.user,
        is_active=True
    )

    if request.method == "POST":
        text = request.POST.get("message", "").strip()
        if text:
            WorkItemMessage.objects.create(
                work_item=work_item,
                sender=request.user,
                sender_role=request.user.login_role,
                message=text
            )
            messages.success(request, "Comment posted.")
            return redirect(
                "user_app:work-item-comments",
                item_id=work_item.id
            )

    messages_qs = work_item.messages.select_related("sender")

    return render(
        request,
        "user/page/work_item_comments.html",
        {
            "work_item": work_item,
            "messages": messages_qs,
        }
    )