# admin_app/views/user_security_views.py

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils.crypto import get_random_string

from accounts.models import User


@login_required
def admin_reset_user_password(request, user_id):
    if request.user.login_role != "admin":
        messages.error(request, "Unauthorized action.")
        return redirect("admin_app:users")

    target_user = get_object_or_404(User, id=user_id)

    if target_user.id == request.user.id:
        messages.error(request, "You cannot reset your own password.")
        return redirect("admin_app:user-profile", user_id=user_id)

    if request.method != "POST":
        return redirect("admin_app:user-profile", user_id=user_id)

    new_password = request.POST.get("new_password", "")
    confirm_password = request.POST.get("confirm_password", "")

    if not new_password or not confirm_password:
        messages.error(request, "All password fields are required.")
        return redirect("admin_app:user-profile", user_id=user_id)

    if new_password != confirm_password:
        messages.error(request, "Passwords do not match.")
        return redirect("admin_app:user-profile", user_id=user_id)

    if len(new_password) < 8:
        messages.error(request, "Password must be at least 8 characters.")
        return redirect("admin_app:user-profile", user_id=user_id)

    target_user.set_password(new_password)
    target_user.save()

    messages.success(request, "Password reset successfully.")
    return redirect("admin_app:user-profile", user_id=user_id)

# admin_app/views/user_security_views.py

@login_required
def admin_delete_user(request, user_id):
    if request.user.login_role != "admin":
        messages.error(request, "Unauthorized action.")
        return redirect("admin_app:users")

    target_user = get_object_or_404(User, id=user_id)

    if target_user.id == request.user.id:
        messages.error(request, "You cannot delete your own account.")
        return redirect("admin_app:user-profile", user_id=user_id)

    if request.method != "POST":
        return redirect("admin_app:user-profile", user_id=user_id)

    username = target_user.username
    target_user.delete()

    messages.success(request, f"User '{username}' has been deleted.")
    return redirect("admin_app:users")
