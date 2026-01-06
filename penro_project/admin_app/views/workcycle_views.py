from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.db.models import Q, F
from django.db.models.deletion import ProtectedError
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
from notifications.services.system import notify_workcycle_edited
from notifications.services.system import (
    notify_workcycle_archive_toggled,
    
)
from notifications.services.system import notify_workcycle_deleted
# ============================================================
# WORK CYCLE LIST
# ============================================================

@login_required
def workcycle_list(request):
    """
    Admin list view for ACTIVE Work Cycles

    Features:
    - Lifecycle filtering (?state=ongoing|due_soon|lapsed)
    - Search by title (?q=)
    - Sort by due date (?sort=due_asc|due_desc)
    - Stats always based on ALL active work cycles
    """

    # =========================================================
    # REQUEST PARAMS
    # =========================================================
    state = request.GET.get("state")
    search_query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort")  # due_asc | due_desc

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
    )

    # =========================================================
    # SORTING (DB-SAFE)
    # =========================================================
    if sort == "due_asc":
        qs = qs.order_by("due_at")
    elif sort == "due_desc":
        qs = qs.order_by("-due_at")
    else:
        qs = qs.order_by("-created_at")  # default

    # Materialize queryset (needed for lifecycle_state property)
    workcycles = list(qs)

    # =========================================================
    # LIFECYCLE FILTER (PROPERTY-SAFE)
    # =========================================================
    if state:
        workcycles = [
            wc for wc in workcycles
            if wc.lifecycle_state == state
        ]

    # =========================================================
    # SEARCH (TITLE)
    # =========================================================
    if search_query:
        q_lower = search_query.lower()
        workcycles = [
            wc for wc in workcycles
            if q_lower in wc.title.lower()
        ]

    # =========================================================
    # STATS (ALWAYS FROM *ALL* ACTIVE)
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
    # UI HELPERS (SAFE, NO ORM ABUSE)
    # =========================================================
    for wc in workcycles:
        wc.has_team_assignment = wc.assignments.filter(
            assigned_team__isnull=False
        ).exists()

    # =========================================================
    # RENDER
    # =========================================================
    return render(
        request,
        "admin/page/workcycles.html",
        {
            "workcycles": workcycles,
            "active_count": len(all_active),
            "lifecycle_counts": lifecycle_counts,
            "current_state": state,
            "search_query": search_query,
            "current_sort": sort,   # 👈 for active ASC/DESC buttons
            "users": User.objects.filter(is_active=True),
            "teams": Team.objects.all(),
            "now": timezone.now(),
        },
    )

@login_required
def inactive_workcycle_list(request):
    """
    Admin list view for INACTIVE (ARCHIVED) Work Cycles

    Filtering via:
      ?year=
      ?month=
      ?q=
      ?sort=due_asc | due_desc

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
    )

    all_inactive = list(qs)        # for stats + filter options
    workcycles = list(all_inactive)

    # =========================================================
    # FILTER PARAMS
    # =========================================================
    year_filter = request.GET.get("year")
    month_filter = request.GET.get("month")
    search_query = request.GET.get("q", "").strip()
    sort_param = request.GET.get("sort")   # 👈 ADD THIS

    # =========================================================
    # APPLY FILTERS (IN MEMORY – MATCHES YOUR CURRENT DESIGN)
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
    # APPLY SORTING (FIXED)
    # =========================================================
    if sort_param == "due_asc":
        workcycles.sort(
            key=lambda wc: wc.due_at or timezone.datetime.max
        )

    elif sort_param == "due_desc":
        workcycles.sort(
            key=lambda wc: wc.due_at or timezone.datetime.min,
            reverse=True
        )

    # =========================================================
    # STATS (ALWAYS BASED ON *ALL* INACTIVE)
    # =========================================================
    inactive_count = len(all_inactive)

    # =========================================================
    # UI STATE
    # =========================================================
    has_filters = any([
        year_filter,
        month_filter,
        search_query,
        sort_param,
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

    # =========================================================
    # RENDER
    # =========================================================
    return render(
        request,
        "admin/page/workcycles-inactive.html",
        {
            "workcycles": workcycles,
            "inactive_count": inactive_count,
            "years": years,
            "months": months,
            "search_query": search_query,
            "has_filters": has_filters,
            "now": timezone.now(),
        },
    )

# ============================================================
# CREATE WORK CYCLE
# ============================================================
@login_required
def create_workcycle(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description", "")

        # -----------------------------
        # DUE DATE (TIMEZONE-SAFE)
        # -----------------------------
        due_at_raw = request.POST.get("due_at")
        due_at = parse_datetime(due_at_raw)

        if not due_at:
            messages.error(request, "Invalid due date.")
            return redirect("admin_app:workcycles")

        if timezone.is_naive(due_at):
            due_at = timezone.make_aware(
                due_at,
                timezone.get_current_timezone()
            )

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
            due_at=due_at,  # ✅ timezone-aware
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
@login_required
def edit_workcycle(request):
    if request.method == "POST":
        wc_id = request.POST.get("workcycle_id")
        workcycle = get_object_or_404(WorkCycle, id=wc_id)

        # 🔥 capture old state BEFORE edit
        old_due_at = workcycle.due_at

        workcycle.title = request.POST.get("title")
        workcycle.description = request.POST.get("description", "")

        due_at_raw = request.POST.get("due_at")
        due_at = parse_datetime(due_at_raw)

        if not due_at:
            messages.error(request, "Invalid due date.")
            return redirect("admin_app:workcycles")

        if timezone.is_naive(due_at):
            due_at = timezone.make_aware(
                due_at,
                timezone.get_current_timezone()
            )

        workcycle.due_at = due_at
        workcycle.save(update_fields=["title", "description", "due_at"])

        # ✅ SYSTEM NOTIFICATION
        notify_workcycle_edited(
            workcycle=workcycle,
            edited_by=request.user,
            old_due_at=old_due_at,
        )

        messages.success(request, "Work cycle updated successfully.")
        return redirect("admin_app:workcycles")

# ============================================================
# REASSIGN WORK CYCLE
# ============================================================
@login_required
def reassign_workcycle(request):
    if request.method != "POST":
        return redirect("admin_app:workcycles")

    if request.user.login_role != "admin":
        messages.error(request, "You are not allowed to perform this action.")
        return redirect("admin_app:workcycles")

    wc_id = request.POST.get("workcycle_id")
    workcycle = get_object_or_404(WorkCycle, id=wc_id)

    # USERS
    raw_user_ids = request.POST.getlist("users[]")
    user_ids = [uid for uid in raw_user_ids if uid.isdigit()]
    users = User.objects.filter(id__in=user_ids)

    # TEAM
    team_id = request.POST.get("team")
    team = Team.objects.filter(id=team_id).first() if team_id else None

    # NOTE
    inactive_note = request.POST.get("inactive_note", "").strip()

    if not users.exists() and not team:
        messages.error(
            request,
            "You must assign at least one user or a team."
        )
        return redirect("admin_app:workcycles")

    reassign_workcycle_service(
        workcycle=workcycle,
        users=users,
        team=team,
        inactive_note=inactive_note,
        performed_by=request.user,  # ✅ correct
    )

    messages.success(request, "Work cycle reassigned successfully.")
    return redirect("admin_app:workcycles")


# ============================================================
# WORK CYCLE ASSIGNMENT DETAILS
# ============================================================

def workcycle_assignments(request, pk):
    # =====================================================
    # LOAD WORK CYCLE
    # =====================================================
    workcycle = get_object_or_404(WorkCycle, pk=pk)

    # =====================================================
    # ASSIGNMENTS
    # =====================================================
    assignments = (
        WorkAssignment.objects
        .filter(workcycle=workcycle)
        .select_related("assigned_user", "assigned_team")
    )

    # =====================================================
    # ACTIVE LIST
    # (active = True) OR (inactive AND archived by owner)
    # =====================================================
    active_items = (
        WorkItem.objects
        .filter(workcycle=workcycle)
        .filter(
            Q(is_active=True)
            |
            Q(
                is_active=False,
                inactive_by=F("owner"),
            )
        )
        .select_related("owner", "workcycle")
    )

    # =====================================================
    # ARCHIVED LIST
    # (inactive AND NOT archived by owner)
    # =====================================================
    archived_items = (
        WorkItem.objects
        .filter(
            workcycle=workcycle,
            is_active=False,
        )
        .exclude(
            inactive_by=F("owner")
        )
        .select_related("owner", "workcycle")
    )

    # ----------------------------------
    # SUBMISSION STATUS CALCULATION
    # ----------------------------------
    for item in list(active_items) + list(archived_items):
        if item.submitted_at:
            delta = item.workcycle.due_at - item.submitted_at

            if delta.total_seconds() >= 0:
                item.submission_status = "on_time"
                item.submission_delta = None
            else:
                late = abs(delta)
                days = late.days
                hours = late.seconds // 3600

                item.submission_delta = (
                    f"{days}d {hours}h" if days > 0 else f"{hours}h"
                )
                item.submission_status = "late"
        else:
            item.submission_status = None
            item.submission_delta = None

    # =====================================================
    # COUNTS (ACTIVE SEMANTICS)
    # =====================================================
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

            # UI buckets
            "active_items": active_items,
            "archived_items": archived_items,

            # Stats
            "status_counts": status_counts,
            "review_counts": review_counts,
        },
    )
# ============================================================
# TOGGLE WORK CYCLE ARCHIVE
# ============================================================

@require_POST
def toggle_workcycle_archive(request, pk):
    """
    Toggle WorkCycle active / archived state.

    - Active → Archived
    - Archived → Restored

    Reminder system automatically respects is_active flag.
    """

    workcycle = get_object_or_404(WorkCycle, pk=pk)

    workcycle.is_active = not workcycle.is_active
    workcycle.save(update_fields=["is_active"])

    # ✅ SYSTEM IN-APP NOTIFICATION
    notify_workcycle_archive_toggled(
        workcycle=workcycle,
        actor=request.user,
    )

    if workcycle.is_active:
        messages.success(
            request,
            "Work cycle restored successfully."
        )
    else:
        messages.success(
            request,
            "Work cycle archived successfully."
        )

    return redirect("admin_app:workcycles")


# ============================================================
# DELETE WORK CYCLE (HARD DELETE)
# ============================================================

@require_POST
def delete_workcycle(request, pk):
    """
    Permanently delete a WorkCycle.

    - If protected by related objects (folders, documents),
      deletion is blocked and user is instructed to archive instead.
    """

    workcycle = get_object_or_404(WorkCycle, pk=pk)

    redirect_to = request.META.get(
        "HTTP_REFERER",
        reverse("admin_app:workcycles")
    )

    try:
        title = workcycle.title

        # 🔥 capture affected users BEFORE delete
        affected_user_ids = list(
            workcycle.work_items
            .values_list("owner_id", flat=True)
            .distinct()
        )

        workcycle.delete()

        # ✅ SYSTEM IN-APP NOTIFICATION
        if affected_user_ids:
            notify_workcycle_deleted(
                workcycle_title=title,
                actor=request.user,
                affected_user_ids=affected_user_ids,
            )

        messages.success(
            request,
            f"Work cycle '{title}' was permanently deleted."
        )

    except ProtectedError:
        messages.error(
            request,
            "This work cycle cannot be deleted because it still has "
            "documents or folders linked to it. "
            "Please archive it instead."
        )

    return redirect(redirect_to)