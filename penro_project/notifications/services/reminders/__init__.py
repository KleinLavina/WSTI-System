"""
Reminder notification service layer.

This package contains time-based reminder emitters
that are triggered by schedulers (management commands,
task schedulers, or background workers).

Reminder logic is:
- service-layer only
- date-based
- deduplicated
- role-agnostic at creation time
"""

# =====================================================
# WORKCYCLE REMINDERS
# =====================================================
from .workcycle import (
    send_workcycle_deadline_reminders,
)

# =====================================================
# WORKITEM REMINDERS
# =====================================================
from .workitem import (
    send_workitem_deadline_reminders,
)

__all__ = [
    # WorkCycle
    "send_workcycle_deadline_reminders",

    # WorkItem
    "send_workitem_deadline_reminders",
]
