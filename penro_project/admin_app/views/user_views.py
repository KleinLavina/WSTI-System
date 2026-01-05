from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.db import IntegrityError
from django.db.models import Q
from accounts.models import User, Team, OrgAssignment
from accounts.forms import UserCreateForm
from django.contrib import messages

@login_required
def users(request):
    """
    Users list view with organizational filtering, search, and sorting.
    """
    # Base queryset with org relationships
    users_qs = (
        User.objects
        .select_related(
            "org_assignment__division",
            "org_assignment__section",
            "org_assignment__service",
            "org_assignment__unit",
        )
    )

    # =====================================================
    # ORGANIZATIONAL FILTERS
    # =====================================================
    current_division = request.GET.get('division')
    current_section = request.GET.get('section')
    current_service = request.GET.get('service')
    current_unit = request.GET.get('unit')

    # Get all divisions for filter dropdown
    divisions = Team.objects.filter(team_type=Team.TeamType.DIVISION).order_by('name')

    # Filter by division
    sections = []
    services = []
    units = []
    
    division_name = None
    section_name = None
    service_name = None
    unit_name = None

    if current_division:
        users_qs = users_qs.filter(org_assignment__division_id=current_division)
        division_obj = Team.objects.filter(id=current_division).first()
        if division_obj:
            division_name = division_obj.name
        
        # Get sections for this division
        sections = Team.objects.filter(
            team_type=Team.TeamType.SECTION,
            parent_id=current_division
        ).order_by('name')

        # Filter by section
        if current_section:
            users_qs = users_qs.filter(org_assignment__section_id=current_section)
            section_obj = Team.objects.filter(id=current_section).first()
            if section_obj:
                section_name = section_obj.name
            
            # Get services for this section
            services = Team.objects.filter(
                team_type=Team.TeamType.SERVICE,
                parent_id=current_section
            ).order_by('name')

            # Get units that belong to section or its services
            units_qs = Team.objects.filter(
                team_type=Team.TeamType.UNIT,
                parent_id=current_section
            )
            
            # Filter by service (optional)
            if current_service:
                users_qs = users_qs.filter(org_assignment__service_id=current_service)
                service_obj = Team.objects.filter(id=current_service).first()
                if service_obj:
                    service_name = service_obj.name
                
                # Units under this service
                units_qs = units_qs | Team.objects.filter(
                    team_type=Team.TeamType.UNIT,
                    parent_id=current_service
                )
            
            units = units_qs.order_by('name')

            # Filter by unit
            if current_unit:
                users_qs = users_qs.filter(org_assignment__unit_id=current_unit)
                unit_obj = Team.objects.filter(id=current_unit).first()
                if unit_obj:
                    unit_name = unit_obj.name

    # =====================================================
    # SEARCH
    # =====================================================
    search_query = request.GET.get('q', '').strip()
    if search_query:
        users_qs = users_qs.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(position_title__icontains=search_query)
        )

    # =====================================================
    # SORTING
    # =====================================================
    current_sort = request.GET.get('sort', 'name_asc')
    
    sort_mapping = {
        'name_asc': ['first_name', 'last_name', 'username'],
        'name_desc': ['-first_name', '-last_name', '-username'],
        'date_desc': ['-date_joined'],
        'date_asc': ['date_joined'],
        'role_asc': ['login_role', 'username'],
    }
    
    sort_fields = sort_mapping.get(current_sort, ['first_name', 'last_name', 'username'])
    users_qs = users_qs.order_by(*sort_fields)

    # =====================================================
    # CONTEXT
    # =====================================================
    form = UserCreateForm()

    context = {
        "users": users_qs,
        "total_users": users_qs.count(),
        "form": form,
        
        # Filter data
        "divisions": divisions,
        "sections": sections,
        "services": services,
        "units": units,
        
        # Current filters
        "current_division": current_division,
        "current_section": current_section,
        "current_service": current_service,
        "current_unit": current_unit,
        
        # Filter names
        "current_division_name": division_name,
        "current_section_name": section_name,
        "current_service_name": service_name,
        "current_unit_name": unit_name,
        
        # Search & Sort
        "search_query": search_query,
        "current_sort": current_sort,
    }

    return render(request, "admin/page/users.html", context)

@login_required
def user_profile(request, user_id):
    """
    Admin view: User Profile (view + inline edit)
    """
    user_obj = get_object_or_404(
        User.objects.select_related(
            "org_assignment__division",
            "org_assignment__section",
            "org_assignment__service",
            "org_assignment__unit",
        ),
        id=user_id,
    )

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()

        # ------------------------------------
        # VALIDATE USERNAME
        # ------------------------------------
        if not username:
            messages.error(request, "Username cannot be empty.")
            return redirect("admin_app:user-profile", user_id=user_obj.id)

        if (
            User.objects
            .exclude(id=user_obj.id)
            .filter(username=username)
            .exists()
        ):
            messages.error(request, "Username is already taken.")
            return redirect("admin_app:user-profile", user_id=user_obj.id)

        # ------------------------------------
        # SAVE FIELDS
        # ------------------------------------
        user_obj.username = username
        user_obj.first_name = request.POST.get("first_name", "").strip()
        user_obj.last_name = request.POST.get("last_name", "").strip()
        user_obj.email = email
        user_obj.position_title = request.POST.get("position_title", "").strip()

        user_obj.save(update_fields=[
            "username",
            "first_name",
            "last_name",
            "email",
            "position_title",
        ])

        messages.success(request, "User profile updated successfully.")

        return redirect("admin_app:user-profile", user_id=user_obj.id)

    return render(
        request,
        "admin/page/user_profile.html",
        {
            "profile_user": user_obj,
        }
    )

@login_required
def user_update_role(request, user_id):
    """
    Admin-only view to update user role
    """
    # Only admins can update roles
    if request.user.login_role != 'admin':
        messages.error(request, "You don't have permission to change user roles.")
        return redirect("admin_app:user-profile", user_id=user_id)

    if request.method != "POST":
        return redirect("admin_app:user-profile", user_id=user_id)

    user_obj = get_object_or_404(User, id=user_id)
    new_role = request.POST.get("login_role", "").strip()

    # Validate role
    if new_role not in ['user', 'admin']:
        messages.error(request, "Invalid role selected.")
        return redirect("admin_app:user-profile", user_id=user_obj.id)

    # Prevent self-demotion (admin removing their own admin role)
    if user_obj.id == request.user.id and new_role == 'user' and request.user.login_role == 'admin':
        messages.error(request, "You cannot remove your own admin privileges.")
        return redirect("admin_app:user-profile", user_id=user_obj.id)

    # Update role
    user_obj.login_role = new_role
    user_obj.save(update_fields=["login_role"])

    messages.success(request, f"User role updated to {user_obj.get_login_role_display()}.")
    return redirect("admin_app:user-profile", user_id=user_obj.id)

@login_required
def user_update_image(request, user_id):
    """
    Update user profile image
    Can be done by admin or the user themselves
    """
    user_obj = get_object_or_404(User, id=user_id)
    
    # Permission check: admin or self
    if request.user.login_role != 'admin' and request.user.id != user_obj.id:
        messages.error(request, "You don't have permission to change this user's profile picture.")
        return redirect("admin_app:user-profile", user_id=user_id)

    if request.method != "POST":
        return redirect("admin_app:user-profile", user_id=user_id)

    # Check if user wants to remove the image
    remove_image = request.POST.get('remove_image') == 'true'
    
    if remove_image:
        # Delete old image file if exists
        if user_obj.profile_image:
            user_obj.profile_image.delete(save=False)
        
        user_obj.profile_image = None
        user_obj.save(update_fields=['profile_image'])
        messages.success(request, "Profile picture removed successfully.")
        return redirect("admin_app:user-profile", user_id=user_obj.id)

    # Handle new image upload
    profile_image = request.FILES.get('profile_image')
    
    if not profile_image:
        messages.error(request, "No image file provided.")
        return redirect("admin_app:user-profile", user_id=user_obj.id)

    # Validate file type
    if not profile_image.content_type.startswith('image/'):
        messages.error(request, "Please upload a valid image file.")
        return redirect("admin_app:user-profile", user_id=user_obj.id)

    # Validate file size (5MB max)
    if profile_image.size > 5 * 1024 * 1024:
        messages.error(request, "Image file size must be less than 5MB.")
        return redirect("admin_app:user-profile", user_id=user_obj.id)

    # Delete old image if exists
    if user_obj.profile_image:
        user_obj.profile_image.delete(save=False)

    # Save new image
    user_obj.profile_image = profile_image
    user_obj.save(update_fields=['profile_image'])

    messages.success(request, "Profile picture updated successfully.")
    return redirect("admin_app:user-profile", user_id=user_obj.id)

@login_required
def create_user(request):
    """
    AJAX-only user creation endpoint.
    Always returns JSON with detailed error messages.
    """

    # ❌ Block GET requests
    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid request method. Please use POST."
            },
            status=405
        )

    form = UserCreateForm(request.POST)

    # ❌ Invalid form → return field-specific errors
    if not form.is_valid():
        # Format errors for better display
        formatted_errors = {}
        for field, errors in form.errors.items():
            if field == '__all__':
                # Non-field errors
                formatted_errors['general'] = [str(e) for e in errors]
            else:
                # Get field label for better error messages
                field_label = str(form.fields[field].label or field.replace('_', ' ').title())
                formatted_errors[field] = [
                    f"{field_label}: {str(error)}" if not str(error).startswith(field_label) else str(error)
                    for error in errors
                ]
        
        return JsonResponse(
            {
                "success": False,
                "errors": formatted_errors,
                "error": "Please correct the errors below."
            },
            status=400
        )

    try:
        # ✅ Create user
        user = form.save()

        # (Optional) Store raw form data for onboarding if you still need it
        request.session[f"user_form_{user.id}"] = dict(request.POST)

        # ✅ SUCCESS (always JSON)
        return JsonResponse(
            {
                "success": True,
                "message": f"User '{user.username}' created successfully!",
                "user_id": user.id,
                "onboard_url": reverse(
                    "admin_app:onboard-division",
                    args=[user.id]
                )
            },
            status=201
        )
    
    except IntegrityError as e:
        # Handle database integrity errors (e.g., duplicate username/email)
        error_message = str(e)
        
        if 'username' in error_message.lower():
            return JsonResponse(
                {
                    "success": False,
                    "error": "This username is already taken. Please choose another one.",
                    "errors": {
                        "username": ["This username is already taken."]
                    }
                },
                status=400
            )
        elif 'email' in error_message.lower():
            return JsonResponse(
                {
                    "success": False,
                    "error": "This email address is already registered.",
                    "errors": {
                        "email": ["This email address is already registered."]
                    }
                },
                status=400
            )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "error": "A database error occurred. The user may already exist."
                },
                status=400
            )
    
    except Exception as e:
        # Catch any other unexpected errors
        return JsonResponse(
            {
                "success": False,
                "error": f"An unexpected error occurred: {str(e)}"
            },
            status=500
        )

# ============================================
# ONBOARDING FLOW
# ============================================

@login_required
def onboard_division(request, user_id):
    """Step 1: Select Division (Modal-ready)"""
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        division_id = request.POST.get("division")

        if not division_id:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "success": False,
                    "error": "Please select a division."
                }, status=400)
            
            # Fallback for non-AJAX
            return render(
                request,
                "admin/page/modals/onboard_division.html",
                {
                    "user": user,
                    "divisions": Team.objects.filter(team_type=Team.TeamType.DIVISION).order_by("name"),
                    "error": "Please select a division.",
                    "step": 1,
                    "total_steps": 4,
                },
            )

        # Save selection to session
        request.session[f"onboard_{user.id}_division"] = division_id

        # If AJAX → return next step URL
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "next": reverse(
                    "admin_app:onboard-section",
                    args=[user.id]
                )
            })

        # Fallback for non-AJAX
        return redirect(
            "admin_app:onboard-section",
            user_id=user.id
        )

    divisions = Team.objects.filter(
        team_type=Team.TeamType.DIVISION
    ).order_by("name")

    return render(
        request,
        "admin/page/modals/onboard_division.html",
        {
            "user": user,
            "divisions": divisions,
            "step": 1,
            "total_steps": 4,
        },
    )

@login_required
def onboard_section(request, user_id):
    user = get_object_or_404(User, id=user_id)
    division_id = request.session.get(f"onboard_{user.id}_division")

    if not division_id:
        return redirect("admin_app:onboard-division", user_id=user.id)

    if request.method == "POST":
        section_id = request.POST.get("section")

        if not section_id:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "success": False,
                    "error": "Please select a section."
                }, status=400)

        if section_id:
            request.session[f"onboard_{user.id}_section"] = section_id

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "success": True,
                    "next": reverse(
                        "admin_app:onboard-service",
                        args=[user.id]
                    )
                })

            return redirect(
                "admin_app:onboard-service",
                user_id=user.id
            )

    sections = Team.objects.filter(
        team_type=Team.TeamType.SECTION,
        parent_id=division_id
    ).order_by("name")

    division = Team.objects.get(id=division_id)

    return render(
        request,
        "admin/page/modals/onboard_section.html",
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
    user = get_object_or_404(User, id=user_id)
    section_id = request.session.get(f"onboard_{user.id}_section")

    if not section_id:
        return redirect("admin_app:onboard-section", user_id=user.id)

    if request.method == "POST":
        service_id = request.POST.get("service")

        if service_id:
            request.session[f"onboard_{user.id}_service"] = service_id

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "next": reverse(
                    "admin_app:onboard-unit",
                    args=[user.id]
                )
            })

        return redirect(
            "admin_app:onboard-unit",
            user_id=user.id
        )

    services = Team.objects.filter(
        team_type=Team.TeamType.SERVICE,
        parent_id=section_id
    ).order_by("name")

    section = Team.objects.get(id=section_id)

    return render(
        request,
        "admin/page/modals/onboard_service.html",
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
    user = get_object_or_404(User, id=user_id)
    section_id = request.session.get(f"onboard_{user.id}_section")
    service_id = request.session.get(f"onboard_{user.id}_service")

    if not section_id:
        return redirect("admin_app:onboard-section", user_id=user.id)

    if request.method == "POST":
        unit_id = request.POST.get("unit")

        if unit_id:
            request.session[f"onboard_{user.id}_unit"] = unit_id

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "next": reverse(
                    "admin_app:onboard-complete",
                    args=[user.id]
                )
            })

        return redirect(
            "admin_app:onboard-complete",
            user_id=user.id
        )

    parent_ids = [section_id]
    if service_id:
        parent_ids.append(service_id)

    units = Team.objects.filter(
        team_type=Team.TeamType.UNIT,
        parent_id__in=parent_ids
    ).order_by("name")

    section = Team.objects.get(id=section_id)
    service = Team.objects.filter(id=service_id).first() if service_id else None

    return render(
        request,
        "admin/page/modals/onboard_unit.html",
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
    """
    Final onboarding step - handles both new users and org reassignment
    """
    user = get_object_or_404(User, id=user_id)

    # Pull onboarding data from session
    division_id = request.session.get(f"onboard_{user.id}_division")
    section_id = request.session.get(f"onboard_{user.id}_section")
    service_id = request.session.get(f"onboard_{user.id}_service")
    unit_id = request.session.get(f"onboard_{user.id}_unit")

    # Safety check
    if not division_id or not section_id:
        return redirect("admin_app:onboard-division", user_id=user.id)

    try:
        # Get team instances
        division = Team.objects.get(id=division_id, team_type=Team.TeamType.DIVISION)
        section = Team.objects.get(id=section_id, team_type=Team.TeamType.SECTION)
        service = Team.objects.get(id=service_id, team_type=Team.TeamType.SERVICE) if service_id else None
        unit = Team.objects.get(id=unit_id, team_type=Team.TeamType.UNIT) if unit_id else None

        # Create or update organization assignment
        org_assignment, created = OrgAssignment.objects.update_or_create(
            user=user,
            defaults={
                "division": division,
                "section": section,
                "service": service,
                "unit": unit,
            }
        )

        # Clear session data
        for key in [
            f"onboard_{user.id}_division",
            f"onboard_{user.id}_section",
            f"onboard_{user.id}_service",
            f"onboard_{user.id}_unit",
            f"user_form_{user.id}",
        ]:
            request.session.pop(key, None)

        return render(request, "admin/page/modals/onboard_complete.html", {
            "user": user,
            "org_assignment": org_assignment,
            "success": True,
            "is_new": created,
        })
    
    except Exception as e:
        return render(request, "admin/page/modals/onboard_complete.html", {
            "user": user,
            "error": f"Failed: {str(e)}",
            "success": False,
        })