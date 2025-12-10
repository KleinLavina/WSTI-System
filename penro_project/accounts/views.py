from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # redirect to ?next=original-page
            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)

            # fallback to role-based redirects
            return redirect_user_by_role(user)

        messages.error(request, "Invalid username or password.")

    return render(request, "auth/login.html")

def redirect_user_by_role(user):
    """
    Redirect users depending on permission_role.
    """
    if user.permission_role == "admin":
        return redirect("/main/admin/")

    elif user.permission_role == "manager":
        return redirect("/main/manager/")

    else:  # regular user
        return redirect("/main/user/")
    
def logout_view(request):
    logout(request)
    return redirect("login")

