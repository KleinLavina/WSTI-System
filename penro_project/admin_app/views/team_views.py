from django.shortcuts import render

def team_views(request):
    return render(request, "admin/page/dashboard.html")
