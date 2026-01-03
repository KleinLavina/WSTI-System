from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.services.reminders.workcycle import (
    send_workcycle_deadline_reminders,
)
from notifications.services.reminders.workitem import (
    send_workitem_deadline_reminders,
)


class Command(BaseCommand):
    help = "Send deadline reminders for work cycles and work items"

    def handle(self, *args, **options):
        now = timezone.now()

        self.stdout.write(
            self.style.NOTICE(
                f"[{now:%Y-%m-%d %H:%M:%S}] Starting deadline reminders"
            )
        )

        send_workcycle_deadline_reminders()
        send_workitem_deadline_reminders()

        self.stdout.write(
            self.style.SUCCESS(
                f"[{now:%Y-%m-%d %H:%M:%S}] Deadline reminders completed"
            )
        )
