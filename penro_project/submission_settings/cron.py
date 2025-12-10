from django.utils import timezone
from django.core.mail import send_mail, BadHeaderError
from django.db import transaction
import logging

from .models import DeadlineReminder, SubmissionStatus, Notification

logger = logging.getLogger(__name__)


def send_deadline_reminders():
    """
    Cron job: run often (eg every 15 minutes).
    - Sends reminders whose reminder_date <= now and is_sent=False.
    - Skips/cancels reminders when the submission is already completed/approved/late.
    - Marks reminders is_sent=True only when handled (sent or intentionally cancelled).
    - Falls back to creating an in-app Notification if email cannot be sent or user has no email.
    """
    now = timezone.now()

    reminders = (
        DeadlineReminder.objects
        .select_related("user", "deadline_setting")
        .filter(is_sent=False, reminder_date__lte=now)
    )

    for reminder in reminders:
        user = reminder.user
        deadline = reminder.deadline_setting

        # Try to locate submission status; if missing, cancel and log
        submission_status = SubmissionStatus.objects.filter(
            deadline_setting=deadline, user=user
        ).first()

        if not submission_status:
            # No status for this user+deadline — mark handled to avoid repeated attempts
            reminder.is_sent = True
            reminder.save(update_fields=["is_sent"])
            logger.warning(
                "No SubmissionStatus for user=%s deadline=%s — marking reminder handled.",
                user.pk, deadline.pk
            )
            continue

        # If user already submitted (complete/approved/late) => mark handled, no email
        if submission_status.status in {"complete", "approved", "late"}:
            reminder.is_sent = True
            reminder.save(update_fields=["is_sent"])
            logger.info(
                "User %s already submitted (status=%s) for deadline %s — cancelling reminder.",
                user.pk, submission_status.status, deadline.pk
            )
            continue

        # If user has no email, create in-app Notification instead of sending email
        if not user.email:
            Notification.objects.create(
                user=user,
                submission_status=submission_status,
                title=f"Reminder: {deadline.title}",
                message=(
                    f"This is a reminder that '{deadline.title}' is due on "
                    f"{deadline.deadline_date}. Please submit your report."
                )
            )
            reminder.is_sent = True
            reminder.save(update_fields=["is_sent"])
            logger.info("Created in-app notification for user %s (no email).", user.pk)
            continue

        # Try to send email — only mark the reminder sent on success
        subject = f"Reminder: {deadline.title} Deadline"
        body = (
            f"Hello {user.get_full_name()},\n\n"
            f"This is a reminder for '{deadline.title}'.\n"
            f"Deadline: {deadline.deadline_date}\n\n"
            "Please submit your report as soon as possible."
        )
        try:
            # wrap sending in a transaction boundary for safety if needed
            with transaction.atomic():
                send_mail(
                    subject=subject,
                    message=body,
                    from_email="noreply@penro-system.com",
                    recipient_list=[user.email],
                    fail_silently=False,
                )

                # mark reminder as sent only after a successful send
                reminder.is_sent = True
                reminder.save(update_fields=["is_sent"])

                logger.info(
                    "Sent deadline reminder to user %s for deadline %s.",
                    user.pk, deadline.pk
                )

        except (BadHeaderError, Exception) as exc:
            # log the problem and create in-app notification as fallback
            logger.exception(
                "Failed to send reminder email to user %s (deadline=%s): %s",
                user.pk, deadline.pk, exc
            )

            # fallback: in-app notification
            Notification.objects.create(
                user=user,
                submission_status=submission_status,
                title=f"Reminder: {deadline.title}",
                message=(
                    f"This is a reminder that '{deadline.title}' is due on "
                    f"{deadline.deadline_date}. We couldn't send an email, "
                    "so this notification is shown in your account."
                )
            )

            # do NOT mark reminder as sent if email failed — you may want to retry later.
            # if you'd rather mark as handled to avoid reattempts, uncomment the next lines:
            # reminder.is_sent = True
            # reminder.save(update_fields=["is_sent"])
