from django.conf import settings
from django.shortcuts import redirect
from django.urls import resolve, Resolver404


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

        self.PUBLIC_PREFIXES = (
            settings.LOGIN_URL,
            "/auth/",
            "/static/",
            "/media/",
            "/penro/django/admin/",  # Django admin (staff only)
        )

    def __call__(self, request):
        path = request.path

        # Allow public paths
        if path.startswith(self.PUBLIC_PREFIXES):
            return self.get_response(request)

        # Block unauthenticated users
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)

        # 🔒 ROLE-BASED ACCESS CONTROL
        role = request.user.login_role

        # Admin app protection
        if path.startswith("/admin/") and role != "admin":
            return redirect("user_app:dashboard")

        # User app protection
        if path.startswith("/user/") and role == "admin":
            return redirect("admin_app:dashboard")

        # Optional: validate URL exists
        try:
            resolve(path)
        except Resolver404:
            # Invalid URL → send to role dashboard
            if role == "admin":
                return redirect("admin_app:dashboard")
            return redirect("user_app:dashboard")

        return self.get_response(request)
