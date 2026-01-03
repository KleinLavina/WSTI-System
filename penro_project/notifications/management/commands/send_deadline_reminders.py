"""
notifications/management/commands/send_deadline_reminders.py

Scheduled command (runs daily at 8 AM).

NEW ROLE:
- Catch-all for any missed signals
- Ensure consistency across the board
- Handle edge cases (manual DB changes, etc.)

Most notifications now happen via signals in real-time.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.services.reminders.workcycle import (
    send_workcycle_deadline_reminders,
)
from notifications.services.reminders.workitem import (
    send_workitem_deadline_reminders,
)


class Command(BaseCommand):
    help = "Send deadline reminders (catch-all for missed real-time signals)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force send reminders even if already sent today',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        
        self.stdout.write(
            self.style.NOTICE(
                f"[{now:%Y-%m-%d %H:%M:%S}] Starting scheduled deadline reminders"
            )
        )

        # These services now use get_or_create with milestone-based deduplication
        # So they're idempotent and safe to run multiple times
        wc_count = send_workcycle_deadline_reminders()
        wi_count = send_workitem_deadline_reminders()

        self.stdout.write(
            self.style.SUCCESS(
                f"[{now:%Y-%m-%d %H:%M:%S}] Completed: "
                f"{wc_count} work cycle reminders, "
                f"{wi_count} work item reminders"
            )
        )