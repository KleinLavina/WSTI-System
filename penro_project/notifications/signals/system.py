# notifications/signals/system.py

from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.models import Notification
from accounts.models import WorkItem


@receiver(post_save, sender=WorkItem)
def workitem_archived_notification(sender, instance, created, **kwargs):
    if created:
        return

    if instance.is_active:
        return

    Notification.objects.create(
        recipient=instance.owner,
        category=Notification.Category.SYSTEM,
        priority=Notification.Priority.INFO,
        title="Work Item Archived",
        message="This work item has been archived by the system.",
        work_item=instance,
    )
