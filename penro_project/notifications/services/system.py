from notifications.models import Notification


def create_removal_notifications(
    *,
    user_ids,
    workcycle,
    reason=None,
):
    """
    SYSTEM notifications
    --------------------
    For users removed from a work cycle.
    """

    message = (
        reason
        or f"You were removed from the work cycle “{workcycle.title}”."
    )

    Notification.objects.bulk_create([
        Notification(
            recipient_id=user_id,
            category=Notification.Category.SYSTEM,
            priority=Notification.Priority.WARNING,
            title="Work assignment changed",
            message=message,
            workcycle=workcycle,
        )
        for user_id in user_ids
    ])
