from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render

from accounts.models import WorkItem, WorkCycle


@staff_member_required
def done_workers_by_workcycle(request, workcycle_id):
    workcycle = get_object_or_404(
        WorkCycle,
        id=workcycle_id,
        is_active=True,  # ✅ respect lifecycle
    )

    base_qs = (
        WorkItem.objects
        .filter(
            workcycle=workcycle,
            is_active=True,   # ✅ exclude archived items
        )
        .select_related("owner")
    )

    # =========================
    # APPROVED (REVIEWED)
    # =========================
    approved_items = base_qs.filter(
        status="done",
        review_decision="approved",
    ).order_by("-reviewed_at", "-submitted_at")

    # =========================
    # SUBMITTED (PENDING / REVISION)
    # =========================
    submitted_items = base_qs.filter(
        status="done",
        review_decision__in=["pending", "revision"],
    ).order_by("-submitted_at")

    # =========================
    # ONGOING
    # =========================
    ongoing_items = base_qs.filter(
        status__in=["working_on_it", "not_started"],
    ).order_by("status", "created_at")

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
