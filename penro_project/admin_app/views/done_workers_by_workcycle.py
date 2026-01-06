from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, F
from django.shortcuts import get_object_or_404, render

from accounts.models import WorkItem, WorkCycle


@staff_member_required
def done_workers_by_workcycle(request, workcycle_id):
    # =====================================================
    # LOAD WORK CYCLE (ACTIVE ONLY)
    # =====================================================
    workcycle = get_object_or_404(
        WorkCycle,
        id=workcycle_id,
        is_active=True,  # ✅ respect lifecycle
    )

    # =====================================================
    # BASE QUERY (ANALYTICS-SAFE)
    # =====================================================
    base_qs = (
        WorkItem.objects
        .filter(workcycle=workcycle)
        .filter(
            Q(is_active=True)
            |
            Q(
                is_active=False,
                inactive_by=F("owner"),  # ✅ user archived own work
            )
        )
        .select_related("owner", "workcycle")
    )

    # =========================
    # APPROVED (REVIEWED)
    # =========================
    approved_items = (
        base_qs
        .filter(
            status="done",
            review_decision="approved",
        )
        .order_by("-reviewed_at", "-submitted_at")
    )

    # =========================
    # SUBMITTED (PENDING / REVISION)
    # =========================
    submitted_items = (
        base_qs
        .filter(
            status="done",
            review_decision__in=["pending", "revision"],
        )
        .order_by("-submitted_at")
    )

    # =========================
    # ONGOING
    # =========================
    ongoing_items = (
        base_qs
        .filter(
            status__in=["working_on_it", "not_started"],
        )
        .order_by("status", "created_at")
    )

    # ======================================================
    # APPLY SUBMISSION STATUS (ON TIME / LATE)
    # ======================================================
    def apply_submission_meta(items):
        for item in items:
            if not item.submitted_at:
                item.submission_status = None
                item.submission_delta = None
                continue

            due_at = item.workcycle.due_at
            submitted_at = item.submitted_at

            if submitted_at > due_at:
                # ❌ LATE
                item.submission_status = "late"

                delta = submitted_at - due_at
                days = delta.days
                hours = delta.seconds // 3600

                if days > 0:
                    item.submission_delta = f"{days}d {hours}h"
                else:
                    item.submission_delta = f"{hours}h"
            else:
                # ✅ ON TIME
                item.submission_status = "on_time"
                item.submission_delta = None

    # Apply logic
    apply_submission_meta(approved_items)
    apply_submission_meta(submitted_items)

    # ======================================================
    # CONTEXT
    # ======================================================
    context = {
        "workcycle": workcycle,

        "approved_items": approved_items,
        "approved_count": approved_items.count(),

        "submitted_items": submitted_items,
        "submitted_count": submitted_items.count(),

        "ongoing_items": ongoing_items,
        "ongoing_count": ongoing_items.count(),
    }

    return render(
        request,
        "admin/page/done_workers_by_workcycle.html",
        context,
    )
