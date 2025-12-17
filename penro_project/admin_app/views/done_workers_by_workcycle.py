from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render

from accounts.models import WorkItem, WorkCycle

@staff_member_required
def done_workers_by_workcycle(request, workcycle_id):
    workcycle = get_object_or_404(WorkCycle, id=workcycle_id)

    approved_items = (
        WorkItem.objects
        .filter(workcycle=workcycle, status="done", review_decision="approved")
        .select_related("owner")
    )

    submitted_items = (
        WorkItem.objects
        .filter(
            workcycle=workcycle,
            status="done",
            review_decision__in=["pending", "revision"],
        )
        .select_related("owner")
    )

    ongoing_items = (
        WorkItem.objects
        .filter(
            workcycle=workcycle,
            status__in=["working_on_it", "not_started"],
        )
        .select_related("owner")
    )

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
