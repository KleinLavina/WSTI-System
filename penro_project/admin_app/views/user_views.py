from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from accounts.models import User, Team, OrgAssignment
from accounts.forms import UserCreateForm

@login_required
def users(request):
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

    return render(
        request,
        "admin/page/users.html",
        {
            "users": users,
            "total_users": users.count(),
        },
    )

@login_required
def create_user(request):
    restore = request.GET.get("restore")
    user_id = request.GET.get("user")

    initial = None

    if restore and user_id:
        session_key = f"user_form_{user_id}"
        initial = request.session.get(session_key)

    if request.method == "POST":
        form = UserCreateForm(request.POST)

        if form.is_valid():
            user = form.save()

            # save user form state
            request.session[f"user_form_{user.id}"] = request.POST

            # Start onboarding flow
            return redirect("admin_app:onboard-division", user_id=user.id)

    else:
        form = UserCreateForm(initial=initial)

    return render(
        request,
        "admin/page/user_create.html",
        {"form": form},
    )


# ============================================
# ONBOARDING FLOW
# ============================================

@login_required
def onboard_division(request, user_id):
    """Step 1: Select Division"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == "POST":
        division_id = request.POST.get("division")
        
        if division_id:
            # Store in session
            request.session[f"onboard_{user.id}_division"] = division_id
            return redirect("admin_app:onboard-section", user_id=user.id)
    
    divisions = Team.objects.filter(team_type=Team.TeamType.DIVISION)
    
    return render(
        request,
        "admin/page/onboard_division.html",
        {
            "user": user,
            "divisions": divisions,
            "step": 1,
            "total_steps": 4,
        },
    )


@login_required
def onboard_section(request, user_id):
    """Step 2: Select Section"""
    user = get_object_or_404(User, id=user_id)
    division_id = request.session.get(f"onboard_{user.id}_division")
    
    if not division_id:
        return redirect("admin_app:onboard-division", user_id=user.id)
    
    if request.method == "POST":
        section_id = request.POST.get("section")
        
        if section_id:
            request.session[f"onboard_{user.id}_section"] = section_id
            return redirect("admin_app:onboard-service", user_id=user.id)
    
    sections = Team.objects.filter(
        team_type=Team.TeamType.SECTION,
        parent_id=division_id
    )
    division = Team.objects.get(id=division_id)
    
    return render(
        request,
        "admin/page/onboard_section.html",
        {
            "user": user,
            "sections": sections,
            "division": division,
            "step": 2,
            "total_steps": 4,
        },
    )


@login_required
def onboard_service(request, user_id):
    """Step 3: Select Service (Optional)"""
    user = get_object_or_404(User, id=user_id)
    section_id = request.session.get(f"onboard_{user.id}_section")
    
    if not section_id:
        return redirect("admin_app:onboard-section", user_id=user.id)
    
    if request.method == "POST":
        service_id = request.POST.get("service")
        
        if service_id:
            request.session[f"onboard_{user.id}_service"] = service_id
        
        # Allow skipping service
        return redirect("admin_app:onboard-unit", user_id=user.id)
    
    services = Team.objects.filter(
        team_type=Team.TeamType.SERVICE,
        parent_id=section_id
    )
    section = Team.objects.get(id=section_id)
    
    return render(
        request,
        "admin/page/onboard_service.html",
        {
            "user": user,
            "services": services,
            "section": section,
            "step": 3,
            "total_steps": 4,
        },
    )


@login_required
def onboard_unit(request, user_id):
    """Step 4: Select Unit (Optional)"""
    user = get_object_or_404(User, id=user_id)
    section_id = request.session.get(f"onboard_{user.id}_section")
    service_id = request.session.get(f"onboard_{user.id}_service")
    
    if not section_id:
        return redirect("admin_app:onboard-section", user_id=user.id)
    
    if request.method == "POST":
        unit_id = request.POST.get("unit")
        
        if unit_id:
            request.session[f"onboard_{user.id}_unit"] = unit_id
        
        # Save organization assignment
        return redirect("admin_app:onboard-complete", user_id=user.id)
    
    # Get units from section or service
    parent_ids = [section_id]
    if service_id:
        parent_ids.append(service_id)
    
    units = Team.objects.filter(
        team_type=Team.TeamType.UNIT,
        parent_id__in=parent_ids
    )
    
    section = Team.objects.get(id=section_id)
    service = Team.objects.filter(id=service_id).first() if service_id else None
    
    return render(
        request,
        "admin/page/onboard_unit.html",
        {
            "user": user,
            "units": units,
            "section": section,
            "service": service,
            "step": 4,
            "total_steps": 4,
        },
    )


@login_required
def onboard_complete(request, user_id):
    """Complete onboarding and save organization assignment"""
    user = get_object_or_404(User, id=user_id)
    
    # Get all selections from session
    division_id = request.session.get(f"onboard_{user.id}_division")
    section_id = request.session.get(f"onboard_{user.id}_section")
    service_id = request.session.get(f"onboard_{user.id}_service")
    unit_id = request.session.get(f"onboard_{user.id}_unit")
    
    if not division_id or not section_id:
        return redirect("admin_app:onboard-division", user_id=user.id)
    
    # Create or update organization assignment with all fields at once
    org_assignment, created = OrgAssignment.objects.update_or_create(
        user=user,
        defaults={
            'division_id': division_id,
            'section_id': section_id,
            'service_id': service_id if service_id else None,
            'unit_id': unit_id if unit_id else None,
        }
    )
    
    # Clear session data
    request.session.pop(f"onboard_{user.id}_division", None)
    request.session.pop(f"onboard_{user.id}_section", None)
    request.session.pop(f"onboard_{user.id}_service", None)
    request.session.pop(f"onboard_{user.id}_unit", None)
    request.session.pop(f"user_form_{user.id}", None)
    
    return render(
        request,
        "admin/page/onboard_complete.html",
        {
            "user": user,
            "org_assignment": org_assignment,
        },
    )