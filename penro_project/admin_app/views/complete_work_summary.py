from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import (
    Count, Q, F, ExpressionWrapper, FloatField
)
from django.db.models.functions import NullIf
from django.shortcuts import render

from accounts.models import WorkItem


@staff_member_required
def completed_work_summary(request):

    # =====================================================
    # BASE QUERY (ACTIVE WORK ITEMS ONLY)
    # =====================================================
    base_qs = WorkItem.objects.filter(
        workcycle__is_active=True,
        is_active=True,
    )

    # =====================================================
    # PER-WORKCYCLE SUMMARY (GROUPED)
    # =====================================================
    summary = (
        base_qs
        .values(
            "workcycle_id",
            "workcycle__title",
            "workcycle__due_at",
        )
        .annotate(
            # COUNTS
            total_workers=Count("id"),
            done_count=Count("id", filter=Q(status="done")),
            not_finished_count=Count(
                "id",
                filter=Q(status__in=["not_started", "working_on_it"])
            ),

            approved_count=Count(
                "id", filter=Q(status="done", review_decision="approved")
            ),
            revision_count=Count(
                "id", filter=Q(status="done", review_decision="revision")
            ),
            pending_review_count=Count(
                "id", filter=Q(status="done", review_decision="pending")
            ),
        )
        .annotate(
            # PERCENTAGES
            done_pct=ExpressionWrapper(
                100.0 * F("done_count") / NullIf(F("total_workers"), 0),
                output_field=FloatField(),
            ),
            not_finished_pct=ExpressionWrapper(
                100.0 * F("not_finished_count") / NullIf(F("total_workers"), 0),
                output_field=FloatField(),
            ),
            approval_pct=ExpressionWrapper(
                100.0 * F("approved_count") / NullIf(F("done_count"), 0),
                output_field=FloatField(),
            ),
        )
        .order_by("workcycle__due_at")
    )

    # =====================================================
    # TOTAL NUMBER OF WORKCYCLES
    # =====================================================
    total_workcycles = summary.count()

    # =====================================================
    # GLOBAL TOTALS (SEPARATE QUERY – THIS IS THE FIX)
    # =====================================================
    totals = {
        "total_workers": base_qs.count(),
        "total_done": base_qs.filter(status="done").count(),
        "total_not_finished": base_qs.filter(
            status__in=["not_started", "working_on_it"]
        ).count(),
        "total_approved": base_qs.filter(
            status="done", review_decision="approved"
        ).count(),
        "total_revision": base_qs.filter(
            status="done", review_decision="revision"
        ).count(),
        "total_pending_review": base_qs.filter(
            status="done", review_decision="pending"
        ).count(),
    }

    return render(
        request,
        "admin/page/completed_work_summary.html",
        {
            "summary": summary,
            "total_workcycles": total_workcycles,
            "totals": totals,
        }
    )
