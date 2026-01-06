from collections import Counter

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import (
    Count, Q, F, ExpressionWrapper, FloatField
)
from django.db.models.functions import NullIf
from django.shortcuts import render

from accounts.models import WorkItem, WorkCycle


@staff_member_required
def completed_work_summary(request):
    """
    Analytics dashboard for completed / ongoing work.

    Rules:
    - Include ACTIVE work items
    - Include INACTIVE work items ONLY if archived by the OWNER
    - Exclude INACTIVE work items archived by ADMIN or others
    """

    # =====================================================
    # REQUEST PARAMS
    # =====================================================
    state = request.GET.get("state")
    q = request.GET.get("q")
    sort = request.GET.get("sort")

    # =====================================================
    # BASE QUERY (ANALYTICS-SAFE)
    # =====================================================
    base_qs = (
        WorkItem.objects
        .filter(workcycle__is_active=True)
        .filter(
            Q(is_active=True)
            |
            Q(
                is_active=False,
                inactive_by=F("owner"),  # ✅ user archived their own work
            )
        )
    )

    # -----------------------------
    # SEARCH (WorkCycle title)
    # -----------------------------
    if q:
        base_qs = base_qs.filter(
            workcycle__title__icontains=q
        )

    # =====================================================
    # PER-WORKCYCLE AGGREGATION
    # =====================================================
    summary_qs = (
        base_qs
        .values(
            "workcycle_id",
            "workcycle__title",
            "workcycle__due_at",
        )
        .annotate(
            # ---------------------------
            # WORK STATUS COUNTS
            # ---------------------------
            total_workers=Count("id"),

            done_count=Count(
                "id",
                filter=Q(status="done")
            ),

            not_finished_count=Count(
                "id",
                filter=Q(status__in=["not_started", "working_on_it"])
            ),

            # ---------------------------
            # REVIEW DECISION COUNTS
            # ---------------------------
            approved_count=Count(
                "id",
                filter=Q(review_decision="approved")
            ),

            revision_count=Count(
                "id",
                filter=Q(review_decision="revision")
            ),

            pending_review_count=Count(
                "id",
                filter=Q(review_decision="pending")
            ),
        )
        .annotate(
            # ---------------------------
            # WORK PROGRESS %
            # ---------------------------
            done_pct=ExpressionWrapper(
                100.0 * F("done_count") / NullIf(F("total_workers"), 0),
                output_field=FloatField(),
            ),

            not_finished_pct=ExpressionWrapper(
                100.0 * F("not_finished_count") / NullIf(F("total_workers"), 0),
                output_field=FloatField(),
            ),

            # ---------------------------
            # REVIEW APPROVAL RATE %
            # ---------------------------
            approval_pct=ExpressionWrapper(
                100.0 * F("approved_count") / NullIf(
                    F("approved_count")
                    + F("revision_count")
                    + F("pending_review_count"),
                    0
                ),
                output_field=FloatField(),
            ),
        )
    )

    # =====================================================
    # SORTING (DUE DATE)
    # =====================================================
    order_by = "workcycle__due_at"
    if sort == "due_desc":
        order_by = "-workcycle__due_at"

    summary_qs = summary_qs.order_by(order_by)

    # =====================================================
    # MATERIALIZE QUERYSET
    # =====================================================
    summary = list(summary_qs)

    # =====================================================
    # LIFECYCLE STATE INJECTION
    # =====================================================
    workcycle_ids = [row["workcycle_id"] for row in summary]

    workcycles = {
        wc.id: wc
        for wc in WorkCycle.objects.filter(id__in=workcycle_ids)
    }

    for row in summary:
        wc = workcycles.get(row["workcycle_id"])

        if not wc:
            state_val = WorkCycle.LifecycleState.ONGOING
        else:
            state_val = wc.lifecycle_state

        row["lifecycle_state"] = state_val

        if state_val == WorkCycle.LifecycleState.DUE_SOON:
            row["lifecycle_label"] = "Due Soon"
            row["lifecycle_icon"] = "fa-hourglass-half"
            row["lifecycle_class"] = "state-due-soon"

        elif state_val == WorkCycle.LifecycleState.LAPSED:
            row["lifecycle_label"] = "Lapsed"
            row["lifecycle_icon"] = "fa-exclamation-triangle"
            row["lifecycle_class"] = "state-lapsed"

        elif state_val == WorkCycle.LifecycleState.ARCHIVED:
            row["lifecycle_label"] = "Archived"
            row["lifecycle_icon"] = "fa-archive"
            row["lifecycle_class"] = "state-archived"

        else:
            row["lifecycle_label"] = "Ongoing"
            row["lifecycle_icon"] = "fa-sync-alt"
            row["lifecycle_class"] = "state-ongoing"

    # =====================================================
    # COPY FULL SUMMARY (FOR STATS)
    # =====================================================
    full_summary = summary[:]

    # =====================================================
    # APPLY LIFECYCLE FILTER (POST-INJECTION)
    # =====================================================
    valid_states = {
        WorkCycle.LifecycleState.ONGOING,
        WorkCycle.LifecycleState.DUE_SOON,
        WorkCycle.LifecycleState.LAPSED,
        WorkCycle.LifecycleState.ARCHIVED,
    }

    if state in valid_states:
        summary = [
            row for row in summary
            if row["lifecycle_state"] == state
        ]

    # =====================================================
    # LIFECYCLE COUNTS
    # =====================================================
    lifecycle_counter = Counter(
        row["lifecycle_state"] for row in full_summary
    )

    # =====================================================
    # GLOBAL TOTALS (HEADER / STATS BAR)
    # =====================================================
    totals = {
        "total_workcycles": len(full_summary),
        "total_workers": base_qs.count(),

        "total_done": base_qs.filter(status="done").count(),
        "total_not_finished": base_qs.filter(
            status__in=["not_started", "working_on_it"]
        ).count(),

        "total_approved": base_qs.filter(
            review_decision="approved"
        ).count(),
        "total_revision": base_qs.filter(
            review_decision="revision"
        ).count(),
        "total_pending_review": base_qs.filter(
            review_decision="pending"
        ).count(),

        "ongoing": lifecycle_counter.get(
            WorkCycle.LifecycleState.ONGOING, 0
        ),
        "due_soon": lifecycle_counter.get(
            WorkCycle.LifecycleState.DUE_SOON, 0
        ),
        "lapsed": lifecycle_counter.get(
            WorkCycle.LifecycleState.LAPSED, 0
        ),
        "archived": lifecycle_counter.get(
            WorkCycle.LifecycleState.ARCHIVED, 0
        ),
    }

    return render(
        request,
        "admin/page/completed_work_summary.html",
        {
            "summary": summary,
            "totals": totals,
        }
    )
