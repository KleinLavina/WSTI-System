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
    create_removal_notifications,
)

# =====================================================
# SYSTEM
# =====================================================
from .system import (
    notify_workcycle_edited,
    notify_workcycle_archive_toggled,
)

# =====================================================
# STATUS
# =====================================================
from .status import (
    notify_work_item_status_changed,
)

# =====================================================
# REMINDERS
# =====================================================
from .reminders import (
    send_workcycle_deadline_reminders,
    send_workitem_deadline_reminders,
)

# =====================================================
# REVIEW
# =====================================================
from .review import (
    notify_work_item_review_changed,
)

# =====================================================
# PUBLIC EXPORTS
# =====================================================
__all__ = [
    # Assignment
    "create_assignment_notifications",
    "create_removal_notifications",

    # System
    "notify_workcycle_edited",
    "notify_workcycle_archive_toggled",

    # Status
    "notify_work_item_status_changed",

    # Reminders
    "send_workcycle_deadline_reminders",
    "send_workitem_deadline_reminders",

    # Review
    "notify_work_item_review_changed",
]
