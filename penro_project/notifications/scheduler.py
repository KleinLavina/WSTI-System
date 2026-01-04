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
    # SCHEDULE: 5× DAILY (EVERY 4 HOURS 48 MINUTES)
    # --------------------------------------------
    _scheduler.add_job(
        run_deadline_reminders,
        trigger="interval",
        hours=4,
        minutes=48,
        id="send_deadline_reminders",
        replace_existing=True,
        max_instances=1,      # Prevent overlapping runs
        coalesce=True,        # Merge missed runs if server was down
    )

    _scheduler.start()

    logger.info(
        "APScheduler started: deadline reminders scheduled every "
        "4 hours and 48 minutes (5× per day)"
    )


def run_deadline_reminders():
    """
    Wrapper job that calls the Django management command.
    Keeps all business logic out of the scheduler.
    """
    now = timezone.now()
    logger.info(f"Running scheduled deadline reminders at {now:%Y-%m-%d %H:%M:%S}")

    call_command("send_deadline_reminders")
