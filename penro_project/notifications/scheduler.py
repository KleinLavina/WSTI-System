from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# ============================================================
# GLOBAL SAFETY LOCK
# Prevents scheduler from starting more than once
# ============================================================
_scheduler = None


def start_scheduler():
    """
    Start APScheduler safely.

    - Respects ENABLE_SCHEDULER setting
    - Prevents double start (Django autoreload, imports)
    - Safe for development and single-process production
    """
    global _scheduler

    # --------------------------------------------
    # DEV / PROD TOGGLE
    # --------------------------------------------
    if not getattr(settings, "ENABLE_SCHEDULER", False):
        logger.info("APScheduler disabled via settings (ENABLE_SCHEDULER=False)")
        return

    # --------------------------------------------
    # SAFETY LOCK (NO DOUBLE START)
    # --------------------------------------------
    if _scheduler is not None:
        logger.info("APScheduler already running, skipping initialization")
        return

    logger.info("Starting APScheduler...")

    _scheduler = BackgroundScheduler(
        timezone=settings.TIME_ZONE
    )

    # --------------------------------------------
    # SCHEDULE: 3× DAILY (5AM, 1PM, 9PM)
    # --------------------------------------------
    _scheduler.add_job(
        run_deadline_reminders,
        trigger="cron",
        hour="5,13,21",
        minute=0,
        id="send_deadline_reminders",
        replace_existing=True,
    )

    _scheduler.start()

    logger.info(
        "APScheduler started: deadline reminders scheduled at "
        "05:00, 13:00, and 21:00"
    )


def run_deadline_reminders():
    """
    Wrapper job that calls the Django management command.
    Keeps all business logic out of the scheduler.
    """
    now = timezone.now()
    logger.info(f"Running scheduled deadline reminders at {now}")

    call_command("send_deadline_reminders")
