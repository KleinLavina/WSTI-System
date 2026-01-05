from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import User
from django.http import HttpResponseForbidden
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
def user_profile(request):
    """
    User profile (view + edit) for the logged-in user.
    Identity is derived strictly from request.user.
    """

    user_obj = (
        User.objects
        .select_related(
            "org_assignment__division",
            "org_assignment__section",
            "org_assignment__service",
            "org_assignment__unit",
        )
        .get(id=request.user.id)
    )

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()

        # -----------------------------
        # VALIDATION
        # -----------------------------
        if not username:
            messages.error(request, "Username cannot be empty.")
            return redirect("user_app:profile")

        if (
            User.objects
            .exclude(id=user_obj.id)
            .filter(username=username)
            .exists()
        ):
            messages.error(request, "Username is already taken.")
            return redirect("user_app:profile")

        # -----------------------------
        # SAVE
        # -----------------------------
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

        messages.success(request, "Profile updated successfully.")
        return redirect("user_app:profile")

    return render(
        request,
        "user/page/user_profile.html",
        {
            "profile_user": user_obj,
        }
    )

@login_required
def user_update_image(request):
    """
    Update logged-in user's profile image.
    No user_id, no URL parameters.
    """

    user_obj = request.user

    if request.method != "POST":
        return redirect("user_app:profile")

    # -----------------------------
    # REMOVE IMAGE
    # -----------------------------
    if request.POST.get("remove_image") == "true":
        if user_obj.profile_image:
            user_obj.profile_image.delete(save=False)

        user_obj.profile_image = None
        user_obj.save(update_fields=["profile_image"])

        messages.success(request, "Profile picture removed successfully.")
        return redirect("user_app:profile")

    # -----------------------------
    # UPLOAD NEW IMAGE
    # -----------------------------
    profile_image = request.FILES.get("profile_image")

    if not profile_image:
        messages.error(request, "No image file provided.")
        return redirect("user_app:profile")

    if not profile_image.content_type.startswith("image/"):
        messages.error(request, "Please upload a valid image file.")
        return redirect("user_app:profile")

    if profile_image.size > 5 * 1024 * 1024:
        messages.error(request, "Image file size must be less than 5MB.")
        return redirect("user_app:profile")

    if user_obj.profile_image:
        user_obj.profile_image.delete(save=False)

    user_obj.profile_image = profile_image
    user_obj.save(update_fields=["profile_image"])

    messages.success(request, "Profile picture updated successfully.")
    return redirect("user_app:profile")


@login_required
def onboard_division(request):
    user = request.user

    if request.method == "POST":
        division_id = request.POST.get("division")

        if not division_id:
            return JsonResponse(
                {"success": False, "error": "Please select a division."},
                status=400
            )

        request.session["onboard_division"] = division_id

        return JsonResponse({
            "success": True,
            "next": reverse("user_app:onboard-section")
        })

    divisions = Team.objects.filter(
        team_type=Team.TeamType.DIVISION
    ).order_by("name")

    return render(
        request,
        "user/page/modals/onboard_division.html",
        {
            "divisions": divisions,
            "step": 1,
            "total_steps": 4,
        }
    )

@login_required
def onboard_section(request):
    division_id = request.session.get("onboard_division")

    if not division_id:
        return redirect("user_app:onboard-division")

    if request.method == "POST":
        section_id = request.POST.get("section")

        if not section_id:
            return JsonResponse(
                {"success": False, "error": "Please select a section."},
                status=400
            )

        request.session["onboard_section"] = section_id

        return JsonResponse({
            "success": True,
            "next": reverse("user_app:onboard-service")
        })

    sections = Team.objects.filter(
        team_type=Team.TeamType.SECTION,
        parent_id=division_id
    ).order_by("name")

    return render(
        request,
        "user/page/modals/onboard_section.html",
        {
            "sections": sections,
            "step": 2,
            "total_steps": 4,
        }
    )

@login_required
def onboard_service(request):
    section_id = request.session.get("onboard_section")

    if not section_id:
        return redirect("user_app:onboard-section")

    if request.method == "POST":
        request.session["onboard_service"] = request.POST.get("service")

        return JsonResponse({
            "success": True,
            "next": reverse("user_app:onboard-unit")
        })

    services = Team.objects.filter(
        team_type=Team.TeamType.SERVICE,
        parent_id=section_id
    ).order_by("name")

    return render(
        request,
        "user/page/modals/onboard_service.html",
        {
            "services": services,
            "step": 3,
            "total_steps": 4,
        }
    )

@login_required
def onboard_unit(request):
    section_id = request.session.get("onboard_section")
    service_id = request.session.get("onboard_service")

    if not section_id:
        return redirect("user_app:onboard-section")

    if request.method == "POST":
        request.session["onboard_unit"] = request.POST.get("unit")

        return JsonResponse({
            "success": True,
            "next": reverse("user_app:onboard-complete")
        })

    parent_ids = [section_id]
    if service_id:
        parent_ids.append(service_id)

    units = Team.objects.filter(
        team_type=Team.TeamType.UNIT,
        parent_id__in=parent_ids
    ).order_by("name")

    return render(
        request,
        "user/page/modals/onboard_unit.html",
        {
            "units": units,
            "step": 4,
            "total_steps": 4,
        }
    )

@login_required
def onboard_complete(request):
    user = request.user

    division_id = request.session.get("onboard_division")
    section_id = request.session.get("onboard_section")
    service_id = request.session.get("onboard_service")
    unit_id = request.session.get("onboard_unit")

    if not division_id or not section_id:
        return redirect("user_app:onboard-division")

    division = Team.objects.get(id=division_id)
    section = Team.objects.get(id=section_id)
    service = Team.objects.filter(id=service_id).first() if service_id else None
    unit = Team.objects.filter(id=unit_id).first() if unit_id else None

    org_assignment, created = OrgAssignment.objects.update_or_create(
        user=user,
        defaults={
            "division": division,
            "section": section,
            "service": service,
            "unit": unit,
        }
    )

    # Clear onboarding session
    for key in [
        "onboard_division",
        "onboard_section",
        "onboard_service",
        "onboard_unit",
    ]:
        request.session.pop(key, None)

    return render(
        request,
        "user/page/modals/onboard_complete.html",
        {
            "org_assignment": org_assignment,
            "success": True,
            "is_new": created,
        }
    )
