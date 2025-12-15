from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings


def login_view(request):
    if request.user.is_authenticated:
        return redirect("root")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)

            if user.login_role == "admin":
                return redirect("admin_app:dashboard")
            else:
                return redirect("user_app:dashboard")

        messages.error(request, "Invalid username or password")

    return render(request, "auth/login.html")


def logout_view(request):
    logout(request)
    return redirect(settings.LOGIN_URL)
