"""
Notification service layer.

Each module (or subpackage) corresponds to a Notification.Category
and exposes functions that emit notifications WITHOUT applying
role-based visibility rules.

Visibility, filtering, and role logic are handled strictly
in inbox / mailbox views.
"""

# =====================================================
# ASSIGNMENT
# =====================================================
from .assignment import (
    create_assignment_notifications,
)

# =====================================================
# SYSTEM
# =====================================================
from .system import (
    create_removal_notifications,
)

# =====================================================
# REMINDERS (PACKAGE)
# =====================================================
from .reminders import (
    send_workcycle_deadline_reminders,
    send_workitem_deadline_reminders,
)


# =====================================================
# MESSAGE
# =====================================================


__all__ = [
    # Assignment
    "create_assignment_notifications",

    # System
    "create_removal_notifications",

    # Reminders
    "send_workcycle_deadline_reminders",
    "send_workitem_deadline_reminders",

    # Status
    "create_status_notifications",

    # Review
    "create_review_notifications",

    # Message
    "create_message_notifications",
]
