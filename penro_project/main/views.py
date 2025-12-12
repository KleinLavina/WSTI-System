from pyexpat.errors import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from datetime import date
from django.shortcuts import render
from django.db.models import Count
from accounts.models import Department, User
from django.shortcuts import render, redirect, get_object_or_404
from datetime import datetime
from submission_settings.models import ReportDeadlineSetting, ReportSubmission, ReportFile
from submission_settings.analytics_models import (
    ReportAnalytics,
    DepartmentDeadlineAnalytics,
    ReportAnalyticsSnapshot,
)



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


from django.utils import timezone
from django.contrib.auth.decorators import login_required

@login_required
def deadline_list(request):
    # Load deadlines and related objects
    deadlines = ReportDeadlineSetting.objects.select_related("department") \
        .prefetch_related("submissions", "submissions__user")

    departments = Department.objects.all()
    enriched = []

    today = timezone.now().date()  # calculate once for performance

    for d in deadlines:
        submissions_qs = d.submissions.all()
        dept_user_count = d.department.users.count()

        # --- Submission-level logic (your update_status_logic) ---
        context_subs = []
        for sub in submissions_qs:
            info = sub.update_status_logic()
            context_subs.append({
                "obj": sub,
                "user": sub.user,
                **info
            })

        # --- Deadline stats ---
        total_expected = dept_user_count
        total_submitted = submissions_qs.count()

        complete_count = submissions_qs.filter(status="complete").count()
        in_progress_count = submissions_qs.filter(status="in_progress").count()
        pending_count = submissions_qs.filter(status="pending").count()
        late_count = submissions_qs.filter(status="late").count()
        late_overdue_count = submissions_qs.filter(status="late_overdue").count()

        # --- Completion percentage ---
        if total_expected > 0:
            completion_pct = round((complete_count / total_expected) * 100)
        else:
            completion_pct = round((complete_count / total_submitted) * 100) if total_submitted else 0

        completion_pct = max(0, min(100, completion_pct))  # clamp 0–100

        # --- Determine if progress should show ---
        if total_expected > 0:
            show_progress = pending_count < total_expected
        else:
            show_progress = (total_submitted > 0 and pending_count < total_submitted)

        # -------------------------------------
        # 🟢 NEW: DAYS REMAINING CALCULATION
        # -------------------------------------
        days_remaining = (d.deadline_date - today).days

        enriched.append({
            "obj": d,
            "department": d.department,

            # submission objects with computed status
            "submissions": context_subs,

            # deadline-level data
            "total_expected": total_expected,
            "total_submitted": total_submitted,
            "complete_count": complete_count,
            "in_progress_count": in_progress_count,
            "pending_count": pending_count,
            "late_count": late_count,
            "late_overdue_count": late_overdue_count,
            "completion_pct": completion_pct,
            "show_progress": show_progress,

            "start_date": d.start_date,
            "deadline_date": d.deadline_date,

            # 🌟 REQUIRED FOR YOUR TEMPLATE
            "days_remaining": days_remaining,
        })

    return render(request, "admin/page/report_deadline_list.html", {
        "deadlines": enriched,
        "departments": departments,
    })

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

    # Delete analytics safely
    ReportAnalyticsSnapshot.objects.filter(analytics__deadline=deadline).delete()
    DepartmentDeadlineAnalytics.objects.filter(deadline=deadline).delete()
    ReportAnalytics.objects.filter(deadline=deadline).delete()

    # Delete submissions + files
    ReportFile.objects.filter(submission__deadline=deadline).delete()
    ReportSubmission.objects.filter(deadline=deadline).delete()

    # Finally delete the deadline itself
    deadline.delete()

    return redirect("main:deadline-list")

@login_required
def deadline_status_view(request, deadline_id):
    deadline = get_object_or_404(
        ReportDeadlineSetting.objects.select_related("department"),
        id=deadline_id
    )

    # Fetch all submissions for this deadline
    submissions = (
        ReportSubmission.objects
        .select_related("user")
        .filter(deadline=deadline)
        .order_by("user__last_name")
    )

    # Attach computed values (remaining days, status, etc.)
    worker_list = []

    for sub in submissions:
        info = sub.update_status_logic()  # from your model
        worker_list.append({
            "obj": sub,
            "user": sub.user,
            **info
        })

    context = {
        "deadline": deadline,
        "workers": worker_list,
    }

    return render(request, "admin/page/deadline_worker_statuses.html", context)
