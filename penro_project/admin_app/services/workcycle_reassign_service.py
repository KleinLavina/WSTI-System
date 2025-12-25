from django.db import transaction
from django.utils import timezone

from accounts.models import WorkItem, WorkAssignment


@transaction.atomic
def reassign_workcycle(
    *,
    workcycle,
    users,
    team=None,
    performed_by=None,
    inactive_note=""
):
    """
    Reassign a work cycle.

    - Deactivates removed users' work items
    - Reactivates or creates work items for new users
    - Replaces work assignments atomically

    IMPORTANT:
    - This function NO LONGER resolves users via TeamMembership
    - `users` must be an explicit iterable of User objects
    """

    # =====================================================
    # 1️⃣ Resolve target users (EXPLICIT ONLY)
    # =====================================================
    target_users = set(users)

    # =====================================================
    # 2️⃣ Existing work items & owners
    # =====================================================
    existing_items = WorkItem.objects.filter(workcycle=workcycle)
    existing_users = {wi.owner for wi in existing_items}

    # =====================================================
    # 3️⃣ Users removed by reassignment
    # =====================================================
    removed_users = existing_users - target_users

    # =====================================================
    # 4️⃣ Deactivate removed users' work items
    # =====================================================
    if removed_users:
        WorkItem.objects.filter(
            workcycle=workcycle,
            owner__in=removed_users,
            is_active=True
        ).update(
            is_active=False,
            inactive_reason="reassigned",
            inactive_note=inactive_note or "Work cycle reassigned",
            inactive_at=timezone.now()
        )

    # =====================================================
    # 5️⃣ Reactivate or create work items for target users
    # =====================================================
    for user in target_users:
        wi, created = WorkItem.objects.get_or_create(
            workcycle=workcycle,
            owner=user,
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

    # =====================================================
    # 6️⃣ Replace work assignments (METADATA ONLY)
    # =====================================================
    WorkAssignment.objects.filter(workcycle=workcycle).delete()

    if team:
        # Team assignment is informational / grouping only
        WorkAssignment.objects.create(
            workcycle=workcycle,
            assigned_team=team
        )
    else:
        # Direct user assignments
        WorkAssignment.objects.bulk_create([
            WorkAssignment(
                workcycle=workcycle,
                assigned_user=user
            )
            for user in target_users
        ])
