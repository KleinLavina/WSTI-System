from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q, F, ExpressionWrapper, FloatField
from django.shortcuts import render

from accounts.models import WorkItem


@staff_member_required
def completed_work_summary(request):
    """
    Analytics per active WorkCycle:
    - Done status count
    - Review decision breakdown
    - Approval percentage
    """

    summary = (
        WorkItem.objects
        .filter(workcycle__is_active=True)
        .values(
            "workcycle_id",
            "workcycle__title",
            "workcycle__due_at",
        )
        .annotate(
            total_workers=Count("id"),

            done_count=Count(
                "id",
                filter=Q(status="done")
            ),

            pending_review_count=Count(
                "id",
                filter=Q(review_decision="pending_review")
            ),

            needs_revision_count=Count(
                "id",
                filter=Q(review_decision="needs_revision")
            ),

            approved_count=Count(
                "id",
                filter=Q(review_decision="approved")
            ),
        )
        .annotate(
            approval_pct=ExpressionWrapper(
                F("approved_count") * 100.0 / F("total_workers"),
                output_field=FloatField()
            )
        )
        .order_by("workcycle__due_at")
    )

    return render(
        request,
        "admin/page/completed_work_summary.html",
        {"summary": summary}
    )
