from email import message_from_string
from django.contrib import messages
from django.shortcuts import render, redirect
from accounts.models import User, Team, WorkCycle
from admin_app.services.workcycle_service import create_workcycle_with_assignments
from django.shortcuts import get_object_or_404
from admin_app.services.workcycle_reassign_service import (
    reassign_workcycle as reassign_workcycle_service
)
from accounts.models import WorkCycle, WorkAssignment, WorkItem, TeamMembership


def workcycle_list(request):
    workcycles = (
        WorkCycle.objects
        .all()
        .prefetch_related("assignments__assigned_team")
        .order_by("-created_at")
    )

    for wc in workcycles:
        wc.has_team_assignment = wc.assignments.filter(
            assigned_team__isnull=False
        ).exists()

    return render(
        request,
        "admin/page/workcycles.html",
        {
            "workcycles": workcycles,
            "users": User.objects.filter(is_active=True),
            "teams": Team.objects.all(),
        },
    )

def create_workcycle(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description", "")
        due_at = request.POST.get("due_at")

        # USERS (from users[])
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

        return redirect("admin_app:workcycles")

    # fallback (not usually used because modal lives in li  st page)
    return render(
        request,
        "admin/page/workcycle_create.html",
        {
            "users": User.objects.filter(is_active=True),
            "teams": Team.objects.all(),
        }
    )

def edit_workcycle(request):
    if request.method == "POST":
        wc_id = request.POST.get("workcycle_id")
        wc = get_object_or_404(WorkCycle, id=wc_id)

        wc.title = request.POST.get("title")
        wc.description = request.POST.get("description", "")
        wc.due_at = request.POST.get("due_at")

        wc.save()

        return redirect("admin_app:workcycles")
    

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

    # Safety check
    if not users.exists() and not team:
        messages.error(request, "You must assign at least one user or a team.")
        return redirect("admin_app:workcycles")

    # Perform reassignment
    reassign_workcycle_service(
        workcycle=workcycle,
        users=users,
        team=team,
        performed_by=request.user,
    )

    messages.success(request, "Work cycle reassigned successfully.")
    return redirect("admin_app:workcycles")

def workcycle_assignments(request, pk):
    workcycle = get_object_or_404(WorkCycle, pk=pk)

    assignments = WorkAssignment.objects.filter(workcycle=workcycle)
    active_items = WorkItem.objects.filter(workcycle=workcycle, is_active=True)
    archived_items = WorkItem.objects.filter(workcycle=workcycle, is_active=False)

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
