from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from submission_settings.models import ReportSubmission, UserNotification, SubmissionReminder

@login_required
def user_dashboard(request):
    return render(request, "user/page/dashboard.html")

@login_required
def my_reports(request):
    submissions = ReportSubmission.objects.filter(user=request.user).select_related("deadline")

    enriched = []
    for sub in submissions:
        info = sub.update_status_logic()

        enriched.append({
            "obj": sub,
            "deadline": sub.deadline,
            **info
        })

    return render(request, "user/page/my_reports.html", {
        "submissions": enriched
    })

@login_required
def my_notifications(request):
    reminders = SubmissionReminder.objects.filter(user=request.user)
    notifications = UserNotification.objects.filter(user=request.user)

    combined = []

    # Convert reminders
    for r in reminders:
        combined.append({
            "type": "Reminder",
            "title": f"Upcoming Deadline: {r.deadline.title}",
            "message": f"Reminder scheduled for {r.reminder_date.strftime('%b %d, %Y %I:%M %p')}",
            "date": r.created_at,
        })

    # Convert notifications
    for n in notifications:
        combined.append({
            "type": "Notification",
            "title": n.title,
            "message": n.message,
            "date": n.created_at,
        })

    # Sort newest first
    combined.sort(key=lambda x: x["date"], reverse=True)

    return render(request, "user/page/my_notifications.html", {
        "items": combined
    })
