from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.shortcuts import render, get_object_or_404
from accounts.models import Team, User
from django.contrib import messages

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
# SORTING HELPERS
# ============================================================

def sort_teams_recursively(teams, sort_by):
    """
    Sort a list of teams based on the sort criteria.
    Also recursively sorts children.
    """
    if not teams:
        return teams
    
    # Define sort key functions
    def get_sort_key(team):
        if sort_by == "name_asc":
            return (team.name.lower(),)
        elif sort_by == "name_desc":
            return (team.name.lower(),)
        elif sort_by == "size_desc":
            return (team.total_user_count,)
        elif sort_by == "size_asc":
            return (team.total_user_count,)
        elif sort_by == "date_desc":
            return (team.created_at,)
        elif sort_by == "date_asc":
            return (team.created_at,)
        else:  # type_name (default)
            # Sort by team type order, then name
            type_order = {
                'division': 1,
                'section': 2,
                'service': 3,
                'unit': 4
            }
            return (type_order.get(team.team_type, 5), team.name.lower())
    
    # Sort the current level
    if sort_by == "name_desc":
        sorted_teams = sorted(teams, key=get_sort_key, reverse=True)
    elif sort_by == "size_desc":
        sorted_teams = sorted(teams, key=get_sort_key, reverse=True)
    elif sort_by == "date_desc":
        sorted_teams = sorted(teams, key=get_sort_key, reverse=True)
    else:
        sorted_teams = sorted(teams, key=get_sort_key)
    
    # Recursively sort children
    for team in sorted_teams:
        if team.children_list:
            team.children_list = sort_teams_recursively(team.children_list, sort_by)
    
    return sorted_teams


# ============================================================
# MANAGE ORGANIZATION (DIVISION CARDS)
# ============================================================

@login_required
def manage_organization(request):

    # --------------------------------------------
    # 1. Get sort parameter
    # --------------------------------------------
    sort_by = request.GET.get("sort", "type_name")
    
    # Validate sort parameter
    valid_sorts = ["type_name", "name_asc", "name_desc", "size_desc", "size_asc", "date_desc", "date_asc"]
    if sort_by not in valid_sorts:
        sort_by = "type_name"

    # --------------------------------------------
    # 2. Load ALL teams
    # --------------------------------------------
    teams = Team.objects.select_related("parent").order_by("team_type", "name")
    team_by_id = {t.id: t for t in teams}

    # Initialize containers
    for t in teams:
        t.children_list = []
        t.users = []
        t.total_user_count = 0
        t.total_subunit_count = 0

    # --------------------------------------------
    # 3. Build tree (manual, fast)
    # --------------------------------------------
    root_teams = []
    for t in teams:
        if t.parent_id and t.parent_id in team_by_id:
            team_by_id[t.parent_id].children_list.append(t)
        else:
            root_teams.append(t)

    # --------------------------------------------
    # 4. Load users + org assignments
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
    # 5. Attach users to LOWEST team only (SAFE)
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
    # 6. Compute accurate counts (MUST happen before sorting)
    # --------------------------------------------
    for division in root_teams:
        compute_user_counts(division)
        compute_subunit_counts(division)

    # --------------------------------------------
    # 7. Apply sorting recursively
    # --------------------------------------------
    root_teams = sort_teams_recursively(root_teams, sort_by)

    # --------------------------------------------
    # 8. Render (pass ALL teams for modal)
    # --------------------------------------------
    return render(
        request,
        "admin/page/manage_organization.html",
        {
            "teams": root_teams,
            "current_sort": sort_by,
            "all_teams": teams,  # ← Pass all teams for the create modal
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

            # ✅ MESSAGE
            messages.success(
                request,
                f"{team.get_team_type_display()} '{team.name}' created successfully.",
                extra_tags="create"
            )

            return JsonResponse({
                "success": True,
                "message": f"{team.get_team_type_display()} '{team.name}' created."
            })

        except Team.DoesNotExist:
            messages.error(request, "Selected parent does not exist.", extra_tags="create")
            return JsonResponse(
                {"success": False, "error": "Parent not found"},
                status=400
            )

        except ValidationError as e:
            messages.error(request, str(e), extra_tags="create")
            return JsonResponse(
                {"success": False, "error": str(e)},
                status=400
            )

    return JsonResponse({"success": False, "error": "Invalid request"}, status=405)

# ============================================================
# EDIT TEAM
# ============================================================
@login_required
@require_http_methods(["POST"])
def edit_team(request):
    team_id = request.POST.get("team_id")
    name = request.POST.get("name", "").strip()

    if not team_id or not name:
        messages.error(request, "Team ID and name are required.", extra_tags="update")
        return JsonResponse(
            {"success": False, "error": "Team ID and name are required"},
            status=400
        )

    try:
        team = Team.objects.get(id=team_id)
        old_name = team.name

        team.name = name
        team.full_clean()
        team.save()

        messages.success(
            request,
            f"'{old_name}' renamed to '{team.name}'.",
            extra_tags="update"
        )

        return JsonResponse({
            "success": True,
            "message": "Team updated successfully."
        })

    except Team.DoesNotExist:
        messages.error(request, "Team not found.", extra_tags="update")
        return JsonResponse(
            {"success": False, "error": "Team not found"},
            status=404
        )

    except ValidationError as e:
        messages.error(request, str(e), extra_tags="update")
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
            messages.error(request, "Team ID is required.", extra_tags="delete")
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

        messages.warning(
            request,
            message,
            extra_tags="delete"
        )

        return JsonResponse({
            "success": True,
            "message": message
        })

    except Team.DoesNotExist:
        messages.error(request, "Team not found.", extra_tags="delete")
        return JsonResponse(
            {"success": False, "error": "Team not found"},
            status=404
        )

    except Exception as e:
        messages.error(request, str(e), extra_tags="delete")
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