from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import (
    WorkItem,
    WorkAssignment,
    OrgAssignment,
)

from notifications.services.assignment import (
    create_assignment_notifications,
    create_removal_notifications,
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

    Rules:
    - Team assignment expands to users via OrgAssignment
    - Removed users' work items are archived
      (inactive_by is ALWAYS set)
    - Added users receive new or reactivated work items
    - Work assignments are fully replaced
    - Emits assignment-related notifications
    """

    # =====================================================
    # VALIDATION
    # =====================================================
    if not performed_by:
        raise ValueError("performed_by (admin user) is required.")

    # =====================================================
    # RESOLVE TARGET USERS
    # =====================================================
    target_user_ids = set()

    # Team → org users
    if team:
        org_users = (
            OrgAssignment.objects
            .filter(
                Q(division=team) |
                Q(section=team) |
                Q(service=team) |
                Q(unit=team)
            )
            .select_related("user")
        )

        for org in org_users:
            target_user_ids.add(org.user_id)

    # Direct users
    for user in users:
        target_user_ids.add(user.id)

    if not target_user_ids:
        raise ValueError("Must assign at least one user or a team.")

    # =====================================================
    # EXISTING WORK ITEMS
    # =====================================================
    existing_items = (
        WorkItem.objects
        .filter(workcycle=workcycle)
        .select_for_update()
    )

    existing_user_ids = set(
        existing_items.values_list("owner_id", flat=True)
    )

    # =====================================================
    # USERS REMOVED FROM ASSIGNMENT
    # =====================================================
    removed_user_ids = existing_user_ids - target_user_ids

    if removed_user_ids:
        now = timezone.now()

        items_to_archive = (
            WorkItem.objects
            .filter(
                workcycle=workcycle,
                owner_id__in=removed_user_ids,
                is_active=True
            )
            .select_for_update()
        )

        for item in items_to_archive:
            item.is_active = False
            item.inactive_reason = "reassigned"
            item.inactive_note = inactive_note or "Work cycle reassigned"
            item.inactive_at = now
            item.inactive_by = performed_by  # ✅ GUARANTEED
            item.save()

        # Notifications for removed users
        create_removal_notifications(
            user_ids=removed_user_ids,
            workcycle=workcycle,
            reason=inactive_note or None,
        )

    # =====================================================
    # ADD / REACTIVATE USERS
    # =====================================================
    for user_id in target_user_ids:
        wi, created = WorkItem.objects.get_or_create(
            workcycle=workcycle,
            owner_id=user_id,
            defaults={
                "status": "not_started",
                "is_active": True,
            }
        )

        # Reactivate previously archived item
        if not created and not wi.is_active:
            wi.is_active = True
            wi.inactive_reason = ""
            wi.inactive_note = ""
            wi.inactive_at = None
            wi.inactive_by = None
            wi.status = "not_started"
            wi.save()

    # =====================================================
    # ASSIGNMENT NOTIFICATIONS (NEW USERS ONLY)
    # =====================================================
    newly_assigned_user_ids = target_user_ids - existing_user_ids

    if newly_assigned_user_ids:
        create_assignment_notifications(
            user_ids=newly_assigned_user_ids,
            workcycle=workcycle,
            assigned_by=performed_by,
        )

    # =====================================================
    # REPLACE WORK ASSIGNMENTS
    # =====================================================
    WorkAssignment.objects.filter(
        workcycle=workcycle
    ).delete()

    if team:
        WorkAssignment.objects.create(
            workcycle=workcycle,
            assigned_team=team
        )

    WorkAssignment.objects.bulk_create([
        WorkAssignment(
            workcycle=workcycle,
            assigned_user_id=user_id
        )
        for user_id in target_user_ids
    ])
