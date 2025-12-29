from django.db.models import Count
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from accounts.models import (
    User,
    Team,
    WorkCycle,
    WorkAssignment,
    WorkItem,
)

from admin_app.services.workcycle_service import (
    create_workcycle_with_assignments,
)

from admin_app.services.workcycle_reassign_service import (
    reassign_workcycle as reassign_workcycle_service,
)


# ============================================================
# WORK CYCLE LIST
# ============================================================

def workcycle_list(request):
    """
    Admin list view for ACTIVE Work Cycles
    Stat-driven filtering via ?state=
    """

    # =========================================================
    # BASE QUERYSET (ACTIVE ONLY)
    # =========================================================
    qs = (
        WorkCycle.objects
        .filter(is_active=True)
        .annotate(
            assignment_count=Count("assignments__id", distinct=True)
        )
        .prefetch_related(
            "assignments__assigned_user",
            "assignments__assigned_team",
        )
        .order_by("-created_at")
    )

    workcycles = list(qs)

    # =========================================================
    # STAT FILTER (FROM CLICKABLE BADGES)
    # =========================================================
    state = request.GET.get("state")  # ongoing | due_soon | lapsed

    if state:
        workcycles = [
            wc for wc in workcycles
            if wc.lifecycle_state == state
        ]

    # =========================================================
    # SEARCH (OPTIONAL, KEEPS UX FLEXIBLE)
    # =========================================================
    search_query = request.GET.get("q", "").strip()
    if search_query:
        q = search_query.lower()
        workcycles = [
            wc for wc in workcycles
            if q in wc.title.lower()
        ]

    # =========================================================
    # STATS (ALWAYS BASED ON *ALL* ACTIVE)
    # =========================================================
    all_active = list(qs)

    lifecycle_counts = {
        "ongoing": 0,
        "due_soon": 0,
        "lapsed": 0,
    }

    for wc in all_active:
        if wc.lifecycle_state in lifecycle_counts:
            lifecycle_counts[wc.lifecycle_state] += 1

    # =========================================================
    # UI HELPERS
    # =========================================================
    for wc in workcycles:
        wc.has_team_assignment = wc.assignments.filter(
            assigned_team__isnull=False
        ).exists()

    return render(
        request,
        "admin/page/workcycles.html",
        {
            "workcycles": workcycles,
            "active_count": len(all_active),
            "lifecycle_counts": lifecycle_counts,
            "current_state": state,   # 👈 for active badge styling
            "search_query": search_query,
            "users": User.objects.filter(is_active=True),
            "teams": Team.objects.all(),
            "now": timezone.now(),
        },
    )

def inactive_workcycle_list(request):
    """
    Admin list view for INACTIVE (ARCHIVED) Work Cycles

    Filtering via:
      ?year=
      ?month=
      ?q=

    Reset state:
      no filters applied → "Total Inactive"
    """

    # =========================================================
    # BASE QUERYSET (INACTIVE ONLY)
    # =========================================================
    qs = (
        WorkCycle.objects
        .filter(is_active=False)
        .annotate(
            assignment_count=Count("assignments__id", distinct=True)
        )
        .prefetch_related(
            "assignments__assigned_user",
            "assignments__assigned_team",
        )
        .order_by("-created_at")
    )

    all_inactive = list(qs)   # for stats + filter options
    workcycles = list(all_inactive)

    # =========================================================
    # FILTER PARAMS
    # =========================================================
    year_filter = request.GET.get("year")
    month_filter = request.GET.get("month")
    search_query = request.GET.get("q", "").strip()

    # =========================================================
    # APPLY FILTERS
    # =========================================================
    if year_filter:
        try:
            year_filter = int(year_filter)
            workcycles = [
                wc for wc in workcycles
                if wc.due_at and wc.due_at.year == year_filter
            ]
        except ValueError:
            pass

    if month_filter:
        try:
            month_filter = int(month_filter)
            workcycles = [
                wc for wc in workcycles
                if wc.due_at and wc.due_at.month == month_filter
            ]
        except ValueError:
            pass

    if search_query:
        q = search_query.lower()
        workcycles = [
            wc for wc in workcycles
            if q in wc.title.lower()
        ]

    # =========================================================
    # STATS (ALWAYS BASED ON *ALL* INACTIVE)
    # =========================================================
    inactive_count = len(all_inactive)

    # =========================================================
    # UI STATE (MIRRORS `current_state` FROM ACTIVE VIEW)
    # =========================================================
    has_filters = any([
        year_filter,
        month_filter,
        search_query,
    ])

    # =========================================================
    # FILTER OPTIONS (BASED ON ALL INACTIVE)
    # =========================================================
    years = sorted({
        wc.due_at.year
        for wc in all_inactive
        if wc.due_at
    })

    months = [
        {"value": 1, "label": "January"},
        {"value": 2, "label": "February"},
        {"value": 3, "label": "March"},
        {"value": 4, "label": "April"},
        {"value": 5, "label": "May"},
        {"value": 6, "label": "June"},
        {"value": 7, "label": "July"},
        {"value": 8, "label": "August"},
        {"value": 9, "label": "September"},
        {"value": 10, "label": "October"},
        {"value": 11, "label": "November"},
        {"value": 12, "label": "December"},
    ]

    return render(
        request,
        "admin/page/workcycles-inactive.html",
        {
            "workcycles": workcycles,
            "inactive_count": inactive_count,
            "years": years,
            "months": months,
            "search_query": search_query,
            "has_filters": has_filters,   # 👈 key for badge selection
            "now": timezone.now(),
        },
    )

# ============================================================
# CREATE WORK CYCLE
# ============================================================

def create_workcycle(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description", "")
        due_at = request.POST.get("due_at")

        # -----------------------------
        # USERS (OPTIONAL)
        # -----------------------------
        raw_user_ids = request.POST.getlist("users[]")
        user_ids = [uid for uid in raw_user_ids if uid.isdigit()]
        users = User.objects.filter(id__in=user_ids)

        # -----------------------------
        # TEAM (OPTIONAL)
        # -----------------------------
        team_id = request.POST.get("team")
        team = Team.objects.filter(id=team_id).first() if team_id else None

        # -----------------------------
        # SAFETY CHECK
        # -----------------------------
        if not users.exists() and not team:
            messages.error(
                request,
                "You must assign at least one user or a team."
            )
            return redirect("admin_app:workcycles")

        # -----------------------------
        # CREATE WORK CYCLE
        # -----------------------------
        create_workcycle_with_assignments(
            title=title,
            description=description,
            due_at=due_at,
            created_by=request.user,
            users=users,
            team=team,
        )

        messages.success(request, "Work cycle created successfully.")
        return redirect("admin_app:workcycles")

    # -----------------------------
    # GET REQUEST
    # -----------------------------
    return render(
        request,
        "admin/page/workcycle_create.html",
        {
            "users": User.objects.filter(is_active=True),
            "teams": Team.objects.all(),
        },
    )
# ============================================================
# EDIT WORK CYCLE
# ============================================================

def edit_workcycle(request):
    if request.method == "POST":
        wc_id = request.POST.get("workcycle_id")
        workcycle = get_object_or_404(WorkCycle, id=wc_id)

        workcycle.title = request.POST.get("title")
        workcycle.description = request.POST.get("description", "")
        workcycle.due_at = request.POST.get("due_at")
        workcycle.save()

        messages.success(request, "Work cycle updated successfully.")
        return redirect("admin_app:workcycles")


# ============================================================
# REASSIGN WORK CYCLE
# ============================================================

def reassign_workcycle(request):
    if request.method != "POST":
        return redirect("admin_app:workcycles")

    wc_id = request.POST.get("workcycle_id")
    workcycle = get_object_or_404(WorkCycle, id=wc_id)

    # -----------------------------
    # USERS (OPTIONAL)
    # -----------------------------
    raw_user_ids = request.POST.getlist("users[]")
    user_ids = [uid for uid in raw_user_ids if uid.isdigit()]
    users = User.objects.filter(id__in=user_ids)

    # -----------------------------
    # TEAM (OPTIONAL)
    # -----------------------------
    team_id = request.POST.get("team")
    team = Team.objects.filter(id=team_id).first() if team_id else None

    # -----------------------------
    # OPTIONAL NOTE
    # -----------------------------
    inactive_note = request.POST.get("inactive_note", "").strip()

    # -----------------------------
    # SAFETY CHECK
    # -----------------------------
    if not users.exists() and not team:
        messages.error(
            request,
            "You must assign at least one user or a team."
        )
        return redirect("admin_app:workcycles")

    # -----------------------------
    # REASSIGN
    # -----------------------------
    reassign_workcycle_service(
        workcycle=workcycle,
        users=users,
        team=team,
        inactive_note=inactive_note,
        performed_by=request.user,
    )

    messages.success(request, "Work cycle reassigned successfully.")
    return redirect("admin_app:workcycles")

# ============================================================
# WORK CYCLE ASSIGNMENT DETAILS
# ============================================================

def workcycle_assignments(request, pk):
    workcycle = get_object_or_404(WorkCycle, pk=pk)

    assignments = (
        WorkAssignment.objects
        .filter(workcycle=workcycle)
        .select_related("assigned_user", "assigned_team")
    )

    active_items = WorkItem.objects.filter(
        workcycle=workcycle,
        is_active=True,
    )

    archived_items = WorkItem.objects.filter(
        workcycle=workcycle,
        is_active=False,
    )
    status_counts = {
        "done": active_items.filter(status="done").count(),
        "working_on_it": active_items.filter(status="working_on_it").count(),
        "not_started": active_items.filter(status="not_started").count(),
    }

    review_counts = {
        "pending": active_items.filter(review_decision="pending").count(),
        "approved": active_items.filter(review_decision="approved").count(),
        "revision": active_items.filter(review_decision="revision").count(),
    }
    return render(
        request,
        "admin/page/workcycle_assignments.html",
        {
            "workcycle": workcycle,
            "assignments": assignments,
            "active_items": active_items,
            "archived_items": archived_items,
            "status_counts": status_counts,   # 👈 new
            "review_counts": review_counts,
        },
    )

from django.views.decorators.http import require_POST

@require_POST
def toggle_workcycle_archive(request, pk):
    workcycle = get_object_or_404(WorkCycle, pk=pk)

    workcycle.is_active = not workcycle.is_active
    workcycle.save(update_fields=["is_active"])

    if workcycle.is_active:
        messages.success(request, "Work cycle restored successfully.")
        return redirect("admin_app:workcycles")
    else:
        messages.success(request, "Work cycle archived successfully.")
        return redirect("admin_app:workcycles")
