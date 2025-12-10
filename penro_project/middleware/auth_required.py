from django.shortcuts import redirect
from django.conf import settings

class LoginRequiredMiddleware:
    """
    Forces login for any page except:
    - login
    - logout
    - admin
    - static files
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        exempt_paths = [
            settings.LOGIN_URL,
            "/auth/login/",
            "/auth/logout/",
            "/static/",
            "/admin/",  # allows Django admin
        ]

        # If user is NOT logged in
        if not request.user.is_authenticated:
            if not any(request.path.startswith(path) for path in exempt_paths):
                # 🚀 DO NOT use request.path — let role logic decide later
                return redirect(settings.LOGIN_URL)

        return self.get_response(request)
