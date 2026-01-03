from django.db import transaction
from django.db.models import Q
    
from accounts.models import (
    WorkCycle,
    WorkAssignment,
    WorkItem,
    OrgAssignment,
)

from notifications.services.assignment import (
    create_assignment_notifications,
)


@transaction.atomic
def create_workcycle_with_assignments(
    *,
    title,
    description,
    due_at,
    created_by,
    users,
    team=None,
):
    """
    Creates a WorkCycle and assigns work via:
    - Direct users
    - OR a team (division / section / service / unit)

    Team assignment EXPANDS to users using OrgAssignment.
    Emits ASSIGNMENT notifications for assigned users.
    """

    if not users.exists() and not team:
        raise ValueError("Must assign at least one user or a team.")

    # =====================================================
    # CREATE WORK CYCLE
    # =====================================================
    workcycle = WorkCycle.objects.create(
        title=title,
        description=description,
        due_at=due_at,
        created_by=created_by,
    )

    assigned_user_ids = set()

    # =====================================================
    # TEAM → USERS (ORG SNAPSHOT)
    # =====================================================
    if team:
        # Team responsibility
        WorkAssignment.objects.create(
            workcycle=workcycle,
            assigned_team=team
        )

        org_users = OrgAssignment.objects.filter(
            Q(division=team) |
            Q(section=team) |
            Q(service=team) |
            Q(unit=team)
        ).select_related("user")

        for org in org_users:
            assigned_user_ids.add(org.user_id)

    # =====================================================
    # DIRECT USERS
    # =====================================================
    for user in users:
        assigned_user_ids.add(user.id)

        WorkAssignment.objects.create(
            workcycle=workcycle,
            assigned_user=user
        )

    # =====================================================
    # CREATE WORK ITEMS (DEDUPED)
    # =====================================================
    for user_id in assigned_user_ids:
        WorkItem.objects.get_or_create(
            workcycle=workcycle,
            owner_id=user_id
        )

    # =====================================================
    # ASSIGNMENT NOTIFICATIONS
    # =====================================================
    if assigned_user_ids:
        create_assignment_notifications(
            user_ids=assigned_user_ids,
            workcycle=workcycle,
            assigned_by=created_by,
        )

    return workcycle
