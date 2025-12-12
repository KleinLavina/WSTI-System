# main/views/department_views.py

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required

from accounts.models import Department, User
from submission_settings.models import (
    ReportDeadlineSetting, ReportSubmission, ReportFile,
    SubmissionReminder, UserNotification
)
from submission_settings.analytics_models import (
    ReportAnalytics, DepartmentDeadlineAnalytics, UserSubmissionAnalytics
)

@login_required
def department_list(request):
    departments = Department.objects.all().prefetch_related("users")
    total_workers = User.objects.filter(department__isnull=False).count()

    return render(request, "admin/page/departments.html", {
        "departments": departments,
        "total_workers": total_workers,
    })


@login_required
def department_create(request):
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description", "")

        if not name:
            messages.error(request, "Department name is required.")
            return redirect("main:departments")

        Department.objects.create(name=name, description=description)
        messages.success(request, "Department created successfully!")

    return redirect("main:departments")


@login_required
def department_edit(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)

    if request.method == "POST":
        dept.name = request.POST.get("name")
        dept.description = request.POST.get("description", "")
        dept.save()

        messages.success(request, "Department updated successfully!")

    return redirect("main:departments")


@login_required
def department_delete(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)

    if request.method == "POST":
        submissions = ReportSubmission.objects.filter(deadline__department=dept)

        UserNotification.objects.filter(submission__in=submissions).delete()
        SubmissionReminder.objects.filter(deadline__department=dept).delete()
        ReportFile.objects.filter(submission__in=submissions).delete()
        submissions.delete()

        dept.report_deadlines.all().delete()
        dept.deadline_analytics.all().delete()
        dept.analytics_by_deadline.all().delete()
        dept.users.all().delete()

        dept.delete()
        messages.success(request, "Department deleted successfully!")

    return redirect("main:departments")
