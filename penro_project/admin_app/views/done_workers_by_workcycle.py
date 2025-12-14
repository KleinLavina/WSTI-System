from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render

from accounts.models import WorkItem, WorkCycle



@staff_member_required
def done_workers_by_workcycle(request, workcycle_id):
    workcycle = get_object_or_404(WorkCycle, id=workcycle_id)

    done_items = (
        WorkItem.objects
        .filter(workcycle=workcycle, status="done")
        .select_related("owner")
        .order_by("owner__username")
    )

    ongoing_items = (
        WorkItem.objects
        .filter(
            workcycle=workcycle,
            status__in=["working_on_it", "not_started"]
        )
        .select_related("owner")
        .order_by("owner__username")
    )

    return render(
        request,
        "admin/page/done_workers_by_workcycle.html",
        {
            "workcycle": workcycle,
            "done_items": done_items,
            "ongoing_items": ongoing_items,
        }
    )