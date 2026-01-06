from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.shortcuts import render, get_object_or_404
from accounts.models import Team, User

import json


# ============================================================
# HELPERS: RECURSIVE COUNTS
# ============================================================

def compute_user_counts(team):
    """
    Recursively count users in this team + all descendants.
    """
    total = len(team.users)

    for child in team.children_list:
        total += compute_user_counts(child)

    team.total_user_count = total
    return total


def compute_subunit_counts(team):
    """
    Recursively count all descendant teams (sections, services, units).
    """
    total = len(team.children_list)

    for child in team.children_list:
        total += compute_subunit_counts(child)

    team.total_subunit_count = total
    return total


# ============================================================
# MANAGE ORGANIZATION (DIVISION CARDS)
# ============================================================

@login_required
def manage_organization(request):

    # --------------------------------------------
    # 1. Load ALL teams
    # --------------------------------------------
    teams = Team.objects.select_related("parent").order_by("team_type", "name")
    team_by_id = {t.id: t for t in teams}
    sort_by = request.GET.get("sort", "type_name")

    # Initialize containers
    for t in teams:
        t.children_list = []
        t.users = []
        t.total_user_count = 0
        t.total_subunit_count = 0

    # --------------------------------------------
    # 2. Build tree (manual, fast)
    # --------------------------------------------
    root_teams = []
    for t in teams:
        if t.parent_id and t.parent_id in team_by_id:
            team_by_id[t.parent_id].children_list.append(t)
        else:
            root_teams.append(t)

    # --------------------------------------------
    # 3. Load users + org assignments
    # --------------------------------------------
    users = (
        User.objects
        .select_related(
            "org_assignment__division",
            "org_assignment__section",
            "org_assignment__service",
            "org_assignment__unit",
        )
        .order_by("username")
    )

    # --------------------------------------------
    # 4. Attach users to LOWEST team only (SAFE)
    # --------------------------------------------
    for user in users:
        org = user.primary_org
        if not org:
            continue

        if org.unit_id and org.unit_id in team_by_id:
            team_by_id[org.unit_id].users.append(user)
        elif org.service_id and org.service_id in team_by_id:
            team_by_id[org.service_id].users.append(user)
        elif org.section_id and org.section_id in team_by_id:
            team_by_id[org.section_id].users.append(user)
        elif org.division_id and org.division_id in team_by_id:
            team_by_id[org.division_id].users.append(user)

    # --------------------------------------------
    # 5. Compute accurate counts (THIS WAS MISSING)
    # --------------------------------------------
    for division in root_teams:
        compute_user_counts(division)
        compute_subunit_counts(division)

    # --------------------------------------------
    # 6. Render
    # --------------------------------------------
    return render(
        request,
        "admin/page/manage_organization.html",
        {
            "teams": root_teams,
            "current_sort": sort_by,
        },
    )

# ============================================================
# CREATE TEAM
# ============================================================

@login_required
def create_team(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        team_type = request.POST.get("team_type")
        parent_id = request.POST.get("parent") or None

        try:
            parent = Team.objects.get(id=parent_id) if parent_id else None

            team = Team(
                name=name,
                team_type=team_type,
                parent=parent,
            )
            team.full_clean()
            team.save()

            return JsonResponse({"success": True})

        except (Team.DoesNotExist, ValidationError) as e:
            return JsonResponse(
                {"success": False, "error": str(e)},
                status=400
            )

    teams = Team.objects.order_by("team_type", "name")
    return render(
        request,
        "admin/page/modals/create_team_modal.html",
        {"teams": teams},
    )


# ============================================================
# EDIT TEAM
# ============================================================

@login_required
@require_http_methods(["POST"])
def edit_team(request):
    team_id = request.POST.get("team_id")
    name = request.POST.get("name", "").strip()

    if not team_id or not name:
        return JsonResponse(
            {"success": False, "error": "Team ID and name are required"},
            status=400
        )

    try:
        team = Team.objects.get(id=team_id)
        team.name = name
        team.full_clean()
        team.save()

        return JsonResponse({"success": True})

    except Team.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Team not found"},
            status=404
        )
    except ValidationError as e:
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=400
        )


# ============================================================
# DELETE TEAM
# ============================================================

@login_required
@require_http_methods(["POST"])
def delete_team(request):
    try:
        data = json.loads(request.body)
        team_id = data.get("team_id")

        if not team_id:
            return JsonResponse(
                {"success": False, "error": "Team ID is required"},
                status=400
            )

        team = Team.objects.get(id=team_id)
        team_name = team.name
        children_count = team.children.count()

        team.delete()

        message = f"'{team_name}' deleted successfully."
        if children_count:
            message += f" {children_count} sub-unit(s) were also removed."

        return JsonResponse({"success": True, "message": message})

    except Team.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Team not found"},
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500
        )


# ============================================================
# VIEW HIERARCHY (SINGLE DIVISION TREE)
# ============================================================

@login_required
def view_hierarchy(request, team_id):

    division = get_object_or_404(Team, id=team_id)

    all_teams = Team.objects.select_related("parent").order_by("team_type", "name")
    team_by_id = {t.id: t for t in all_teams}

    for t in all_teams:
        t.children_list = []
        t.users = []
        t.total_user_count = 0

    # Build tree
    for t in all_teams:
        if t.parent_id and t.parent_id in team_by_id:
            team_by_id[t.parent_id].children_list.append(t)

    # Load users
    users = (
        User.objects
        .select_related(
            "org_assignment__division",
            "org_assignment__section",
            "org_assignment__service",
            "org_assignment__unit",
        )
        .order_by("username")
    )

    # Attach users within this division only
    for user in users:
        org = user.primary_org
        if not org or org.division_id != division.id:
            continue

        if org.unit_id:
            team_by_id[org.unit_id].users.append(user)
        elif org.service_id:
            team_by_id[org.service_id].users.append(user)
        elif org.section_id:
            team_by_id[org.section_id].users.append(user)
        else:
            team_by_id[org.division_id].users.append(user)

    division = team_by_id[division.id]
    compute_user_counts(division)

    return render(
        request,
        "admin/page/view_hierarchy.html",
        {"division": division},
    )
