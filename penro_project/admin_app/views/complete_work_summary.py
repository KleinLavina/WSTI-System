from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q, F, ExpressionWrapper, FloatField
from django.db.models.functions import NullIf
from django.shortcuts import render
from accounts.models import WorkItem


@staff_member_required
def completed_work_summary(request):

    summary = (
        WorkItem.objects
        .filter(
            workcycle__is_active=True,
            is_active=True,
        )
        .values(
            "workcycle_id",
            "workcycle__title",
            "workcycle__due_at",
        )
        .annotate(
            # TOTAL
            total_workers=Count("id"),

            # DONE
            done_count=Count(
                "id",
                filter=Q(status="done")
            ),

            # NOT FINISHED = not_started + working_on_it
            not_finished_count=Count(
                "id",
                filter=Q(status__in=["not_started", "working_on_it"])
            ),

            # REVIEW COUNTS
            approved_count=Count(
                "id",
                filter=Q(status="done", review_decision="approved")
            ),
            revision_count=Count(
                "id",
                filter=Q(status="done", review_decision="revision")
            ),
            pending_review_count=Count(
                "id",
                filter=Q(status="done", review_decision="pending")
            ),
        )
        .annotate(
            # STATUS PROGRESS %
            done_pct=ExpressionWrapper(
                100.0 * F("done_count") / NullIf(F("total_workers"), 0),
                output_field=FloatField()
            ),
            not_finished_pct=ExpressionWrapper(
                100.0 * F("not_finished_count") / NullIf(F("total_workers"), 0),
                output_field=FloatField()
            ),

            # APPROVAL %
            approval_pct=ExpressionWrapper(
                100.0 * F("approved_count") / NullIf(F("done_count"), 0),
                output_field=FloatField()
            ),
        )
        .order_by("workcycle__due_at")
    )

    return render(
        request,
        "admin/page/completed_work_summary.html",
        {"summary": summary}
    )
