from django.apps import AppConfig
import os


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"

    def ready(self):
        # --------------------------------------------------
        # Load signals (REQUIRED)
        # --------------------------------------------------
        import notifications.signals  # noqa

        # --------------------------------------------------
        # Start APScheduler SAFELY
        # --------------------------------------------------
        # Prevent duplicate scheduler from Django autoreload
        if os.environ.get("RUN_MAIN") != "true":
            return

        from .scheduler import start_scheduler
        start_scheduler()
