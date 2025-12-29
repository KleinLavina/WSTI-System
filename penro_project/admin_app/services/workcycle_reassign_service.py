from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import (
    WorkItem,
    WorkAssignment,
    OrgAssignment,
)


@transaction.atomic
def reassign_workcycle(
    *,
    workcycle,
    users,
    team=None,
    performed_by=None,
    inactive_note="",
):
    """
    Reassign a work cycle.

    - Team assignment expands to users via OrgAssignment
    - Removed users' work items are archived
    - Added users receive new or reactivated work items
    - Work assignments are fully replaced
    """

    # ============================
    # RESOLVE TARGET USERS
    # ============================
    target_user_ids = set()

    # Team → org users
    if team:
        org_users = OrgAssignment.objects.filter(
            Q(division=team) |
            Q(section=team) |
            Q(service=team) |
            Q(unit=team)
        ).select_related("user")

        for org in org_users:
            target_user_ids.add(org.user_id)

    # Direct users
    for user in users:
        target_user_ids.add(user.id)

    if not target_user_ids and not team:
        raise ValueError("Must assign at least one user or a team.")

    # ============================
    # EXISTING WORK ITEMS
    # ============================
    existing_items = WorkItem.objects.filter(workcycle=workcycle)
    existing_user_ids = set(
        existing_items.values_list("owner_id", flat=True)
    )

    # ============================
    # USERS REMOVED
    # ============================
    removed_user_ids = existing_user_ids - target_user_ids

    if removed_user_ids:
        WorkItem.objects.filter(
            workcycle=workcycle,
            owner_id__in=removed_user_ids,
            is_active=True
        ).update(
            is_active=False,
            inactive_reason="reassigned",
            inactive_note=inactive_note or "Work cycle reassigned",
            inactive_at=timezone.now()
        )

    # ============================
    # ADD / REACTIVATE USERS
    # ============================
    for user_id in target_user_ids:
        wi, created = WorkItem.objects.get_or_create(
            workcycle=workcycle,
            owner_id=user_id,
            defaults={
                "status": "not_started",
                "is_active": True,
            }
        )

        if not created and not wi.is_active:
            wi.is_active = True
            wi.inactive_reason = ""
            wi.inactive_note = ""
            wi.inactive_at = None
            wi.status = "not_started"
            wi.save(update_fields=[
                "is_active",
                "inactive_reason",
                "inactive_note",
                "inactive_at",
                "status",
            ])

    # ============================
    # REPLACE ASSIGNMENTS
    # ============================
    WorkAssignment.objects.filter(workcycle=workcycle).delete()

    if team:
        # Team responsibility
        WorkAssignment.objects.create(
            workcycle=workcycle,
            assigned_team=team
        )

    # Direct user responsibility
    WorkAssignment.objects.bulk_create([
        WorkAssignment(
            workcycle=workcycle,
            assigned_user_id=user_id
        )
        for user_id in target_user_ids
    ])
