from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required

from accounts.models import Department, User
from submission_settings.models import (
    ReportSubmission, ReportFile, SubmissionReminder, UserNotification
)
from submission_settings.analytics_models import UserSubmissionAnalytics


@login_required
def workers_by_department(request, dept_id):
    all_departments = Department.objects.all()

    if dept_id == 0:
        workers = User.objects.filter(department__isnull=False)
        dept_name = "All Workers"
    else:
        dept = get_object_or_404(Department, id=dept_id)
        workers = dept.users.all()
        dept_name = dept.name

    return render(request, "admin/page/workers.html", {
        "dept_name": dept_name,
        "workers": workers,
        "dept_id": dept_id,
        "all_departments": all_departments,
    })


@login_required
def worker_create(request, dept_id):
    if request.method == "POST":
        password = request.POST["password"]
        confirm = request.POST["confirm_password"]

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect("main:workers", dept_id=dept_id)

        User.objects.create_user(
            username=request.POST["username"],
            password=password,
            first_name=request.POST.get("first_name", ""),
            last_name=request.POST.get("last_name", ""),
            position_title=request.POST.get("position_title", ""),
            contact_number=request.POST.get("contact_number", ""),
            department_id=request.POST.get("department"),
            permission_role="user",
        )

        messages.success(request, "Worker created successfully!")
        return redirect("main:workers", dept_id=dept_id)

    return redirect("main:workers", dept_id=dept_id)


@login_required
def worker_edit(request, dept_id, worker_id):
    worker = get_object_or_404(User, id=worker_id)

    if request.method == "POST":
        worker.first_name = request.POST.get("first_name", "")
        worker.last_name = request.POST.get("last_name", "")
        worker.username = request.POST.get("username", worker.username)
        worker.position_title = request.POST.get("position_title", "")
        worker.contact_number = request.POST.get("contact_number", "")
        worker.department_id = request.POST.get("department")
        worker.save()

        return redirect("main:workers", dept_id=dept_id)

    return redirect("main:workers", dept_id=dept_id)


@login_required
def worker_delete(request, dept_id, worker_id):
    worker = get_object_or_404(User, id=worker_id)

    if request.method == "POST":
        ReportFile.objects.filter(submission__user=worker).delete()
        ReportSubmission.objects.filter(user=worker).delete()
        SubmissionReminder.objects.filter(user=worker).delete()
        UserNotification.objects.filter(user=worker).delete()
        UserSubmissionAnalytics.objects.filter(user=worker).delete()
        worker.delete()

    return redirect("main:workers", dept_id=dept_id)
