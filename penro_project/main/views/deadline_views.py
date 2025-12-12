# main/views/deadline_views.py

from datetime import datetime
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required

from accounts.models import Department
from submission_settings.models import (
    ReportDeadlineSetting, ReportSubmission, ReportFile,
)
from submission_settings.analytics_models import (
    ReportAnalytics, DepartmentDeadlineAnalytics,
    ReportAnalyticsSnapshot
)


@login_required
def deadline_list(request):
    deadlines = ReportDeadlineSetting.objects.select_related("department") \
        .prefetch_related("submissions", "submissions__user")

    departments = Department.objects.all()
    enriched = []
    today = timezone.now().date()

    for d in deadlines:
        submissions_qs = d.submissions.all()
        dept_user_count = d.department.users.count()

        subs_data = []
        for sub in submissions_qs:
            info = sub.update_status_logic()
            subs_data.append({"obj": sub, "user": sub.user, **info})

        total_expected = dept_user_count
        complete_count = submissions_qs.filter(status="complete").count()
        pending_count = submissions_qs.filter(status="pending").count()

        completion_pct = (
            round((complete_count / total_expected) * 100)
            if total_expected > 0 else 0
        )

        days_remaining = (d.deadline_date - today).days

        enriched.append({
            "obj": d,
            "department": d.department,
            "submissions": subs_data,
            "total_expected": total_expected,
            "complete_count": complete_count,
            "pending_count": pending_count,
            "completion_pct": completion_pct,
            "days_remaining": days_remaining,
        })

    return render(request, "admin/page/report_deadline_list.html", {
        "deadlines": enriched,
        "departments": departments,
    })


@login_required
def deadline_create(request):
    if request.method == "POST":
        start = datetime.strptime(request.POST["start_date"], "%Y-%m-%d").date()
        end = datetime.strptime(request.POST["deadline_date"], "%Y-%m-%d").date()

        ReportDeadlineSetting.objects.create(
            department_id=request.POST["department"],
            title=request.POST["title"],
            description=request.POST["description"],
            start_date=start,
            deadline_date=end,
        )

    return redirect("main:deadline-list")


@login_required
def deadline_edit(request, pk):
    deadline = get_object_or_404(ReportDeadlineSetting, pk=pk)

    if request.method == "POST":
        deadline.department_id = request.POST.get("department")
        deadline.title = request.POST.get("title")
        deadline.description = request.POST.get("description")
        deadline.start_date = request.POST.get("start_date")
        deadline.deadline_date = request.POST.get("deadline_date")
        deadline.save()

    return redirect("main:deadline-list")


@login_required
def deadline_delete(request, pk):
    deadline = get_object_or_404(ReportDeadlineSetting, pk=pk)

    ReportAnalyticsSnapshot.objects.filter(analytics__deadline=deadline).delete()
    DepartmentDeadlineAnalytics.objects.filter(deadline=deadline).delete()
    ReportAnalytics.objects.filter(deadline=deadline).delete()
    ReportFile.objects.filter(submission__deadline=deadline).delete()
    ReportSubmission.objects.filter(deadline=deadline).delete()
    deadline.delete()

    return redirect("main:deadline-list")


@login_required
def deadline_status_view(request, deadline_id):
    deadline = get_object_or_404(
        ReportDeadlineSetting.objects.select_related("department"),
        id=deadline_id
    )

    submissions = (
        ReportSubmission.objects
        .select_related("user")
        .filter(deadline=deadline)
        .order_by("user__last_name")
    )

    workers = []
    for sub in submissions:
        info = sub.update_status_logic()
        workers.append({"obj": sub, "user": sub.user, **info})

    return render(request, "admin/page/deadline_worker_statuses.html", {
        "deadline": deadline,
        "workers": workers,
    })
