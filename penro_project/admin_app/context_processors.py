# admin_app/context_processors.py

from django.core.cache import cache

from accounts.models import (
    WorkItem,
    WorkItemReadState,
)


def admin_unread_discussions(request):
    """
    Global unread discussion count for ADMIN.

    Uses Facebook-style cursor-based read receipts.

    Template usage:
        {% if admin_has_unread_discussions %}
            <span class="badge">{{ admin_unread_discussions_count }}</span>
        {% endif %}
    """

    if not request.user.is_authenticated:
        return {
            "admin_unread_discussions_count": 0,
            "admin_has_unread_discussions": False,
        }

    total_unread = 0

    work_items = (
        WorkItem.objects
        .filter(is_active=True)
        .prefetch_related("messages", "read_states")
    )

    for item in work_items:
        # --------------------------------------------
        # READ CURSOR FOR THIS ADMIN
        # --------------------------------------------
        read_state = next(
            (
                rs for rs in item.read_states.all()
                if rs.user_id == request.user.id
            ),
            None,
        )

        last_read_id = read_state.last_read_message_id if read_state else 0

        # --------------------------------------------
        # UNREAD COUNT (OTHER PARTY ONLY)
        # --------------------------------------------
        unread = (
            item.messages
            .filter(id__gt=last_read_id)
            .exclude(sender=request.user)
            .count()
        )

        total_unread += unread

    return {
        "admin_unread_discussions_count": total_unread,
        "admin_has_unread_discussions": total_unread > 0,
    }
