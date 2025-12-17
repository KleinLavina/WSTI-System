from django.db import transaction
from django.utils import timezone
from accounts.models import WorkItem, WorkAssignment, TeamMembership


@transaction.atomic
def reassign_workcycle(*, workcycle, users, team, performed_by, inactive_note=""):
    """
    Reassign a work cycle.
    - Deactivates removed users' work items with reason
    - Reactivates or creates work items for new users
    - Replaces work assignments atomically
    """

    # 1️⃣ Resolve target users
    target_users = set()

    if team:
        members = TeamMembership.objects.filter(team=team).select_related("user")
        target_users.update(m.user for m in members)

    target_users.update(users)

    # 2️⃣ Existing work items & users
    existing_items = WorkItem.objects.filter(workcycle=workcycle)
    existing_users = {wi.owner for wi in existing_items}

    # 3️⃣ Users removed by reassignment
    removed_users = existing_users - target_users

    # 4️⃣ Deactivate removed users' work items (WITH CONTEXT)
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

    # 5️⃣ Reactivate or create work items for target users
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

    # 6️⃣ Replace assignments
    WorkAssignment.objects.filter(workcycle=workcycle).delete()

    if team:
        WorkAssignment.objects.create(
            workcycle=workcycle,
            assigned_team=team
        )
    else:
        WorkAssignment.objects.bulk_create([
            WorkAssignment(workcycle=workcycle, assigned_user=user)
            for user in users
        ])
