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
    Admin list view for Work Cycles with:
    - lifecycle filtering
    - year/month filtering
    - admin state stats
    - lifecycle stats
    """

    # =========================================================
    # BASE QUERYSET
    # =========================================================
    workcycles_qs = (
        WorkCycle.objects
        .annotate(
            assignment_count=Count("assignments__id", distinct=True)
        )
        .prefetch_related(
            "assignments__assigned_user",
            "assignments__assigned_team",
        )
        .order_by("-created_at")
    )

    # Convert to list ONCE (we will do python-level filtering)
    workcycles = list(workcycles_qs)

    # =========================================================
    # FILTER PARAMS
    # =========================================================
    lifecycle_filter = request.GET.get("lifecycle")  # ongoing / due_soon / lapsed
    year_filter = request.GET.get("year")
    month_filter = request.GET.get("month")

    # =========================================================
    # APPLY FILTERS (SAFE ORDER)
    # =========================================================
    if lifecycle_filter:
        workcycles = [
            wc for wc in workcycles
            if wc.lifecycle_state == lifecycle_filter
        ]

    if year_filter:
        try:
            year_filter = int(year_filter)
            workcycles = [
                wc for wc in workcycles
                if wc.due_at.year == year_filter
            ]
        except ValueError:
            pass

    if month_filter:
        try:
            month_filter = int(month_filter)
            workcycles = [
                wc for wc in workcycles
                if wc.due_at.month == month_filter
            ]
        except ValueError:
            pass

    # =========================================================
    # ADMIN STATE COUNTS
    # =========================================================
    active_count = sum(1 for wc in workcycles if wc.is_active)
    inactive_count = sum(1 for wc in workcycles if not wc.is_active)

    # =========================================================
    # LIFECYCLE COUNTS
    # =========================================================
    lifecycle_counts = {
        "ongoing": 0,
        "due_soon": 0,
        "lapsed": 0,
    }

    for wc in workcycles:
        lifecycle = wc.lifecycle_state
        if lifecycle in lifecycle_counts:
            lifecycle_counts[lifecycle] += 1

    # =========================================================
    # HELPER FLAGS (OPTIONAL UI HELPERS)
    # =========================================================
    for wc in workcycles:
        wc.has_team_assignment = wc.assignments.filter(
            assigned_team__isnull=False
        ).exists()

    # =========================================================
    # FILTER OPTIONS (YEAR / MONTH DROPDOWNS)
    # =========================================================
    years = sorted({wc.due_at.year for wc in workcycles})

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

    # =========================================================
    # RENDER
    # =========================================================
    return render(
        request,
        "admin/page/workcycles.html",
        {
            "workcycles": workcycles,

            # Stats
            "active_count": active_count,
            "inactive_count": inactive_count,
            "lifecycle_counts": lifecycle_counts,

            # Filter options
            "years": years,
            "months": months,

            # Common context
            "users": User.objects.filter(is_active=True),
            "teams": Team.objects.all(),
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

        # USERS
        raw_user_ids = request.POST.getlist("users[]")
        user_ids = [uid for uid in raw_user_ids if uid.isdigit()]
        users = User.objects.filter(id__in=user_ids)

        # TEAM (optional)
        team_id = request.POST.get("team")
        team = Team.objects.filter(id=team_id).first() if team_id else None

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

    # Fallback (rarely used)
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

    # USERS (optional)
    raw_user_ids = request.POST.getlist("users[]")
    user_ids = [uid for uid in raw_user_ids if uid.isdigit()]
    users = User.objects.filter(id__in=user_ids)

    # TEAM (optional)
    team_id = request.POST.get("team")
    team = Team.objects.filter(id=team_id).first() if team_id else None

    # OPTIONAL NOTE
    inactive_note = request.POST.get("inactive_note", "").strip()

    # SAFETY CHECK
    if not users.exists() and not team:
        messages.error(
            request,
            "You must assign at least one user or a team."
        )
        return redirect("admin_app:workcycles")

    # BUSINESS LOGIC (SERVICE)
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

    return render(
        request,
        "admin/page/workcycle_assignments.html",
        {
            "workcycle": workcycle,
            "assignments": assignments,
            "active_items": active_items,
            "archived_items": archived_items,
        },
    )
