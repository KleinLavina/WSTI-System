from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from accounts.models import Department, User

@login_required
def admin_dashboard(request):
    return render(request, "admin/page/dashboard.html")

@login_required
def department_list(request):
    departments = Department.objects.all().prefetch_related("users")
    total_workers = User.objects.filter(department__isnull=False).count()

    return render(request, "admin/page/departments.html", {
        "departments": departments,
        "total_workers": total_workers,
    })

def workers_by_department(request, dept_id):
    if dept_id == 0:  # Special “All Workers”
        workers = User.objects.filter(department__isnull=False)
        dept_name = "All Workers"
    else:
        dept = get_object_or_404(Department, id=dept_id)
        workers = dept.users.all()
        dept_name = dept.name

    return render(request, "admin/page/workers.html", {
        "dept_name": dept_name,
        "workers": workers,
    })



@login_required
def user_dashboard(request):
    return render(request, "user/page/dashboard.html")
