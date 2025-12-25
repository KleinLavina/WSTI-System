from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from structure.models import DocumentFolder
from accounts.models import OrgAssignment


# ============================================================
# PERMISSION CHECK
# ============================================================

def assert_can_upload(*, work_item, actor):
    """
    Admins can upload anything.
    Users can only upload to their own work items.
    """
    if actor.login_role == "admin":
        return

    if work_item.owner_id != actor.id:
        raise PermissionDenied(
            "You are not allowed to upload attachments for this work item."
        )


# ============================================================
# SAFE FOLDER CREATION
# ============================================================

def get_or_create_folder(
    *,
    name,
    folder_type,
    parent,
    workcycle=None,
    created_by=None,
    system=True,
):
    folder, _ = DocumentFolder.objects.get_or_create(
        parent=parent,
        name=name,
        defaults={
            "folder_type": folder_type,
            "workcycle": workcycle,
            "created_by": created_by,
            "is_system_generated": system,
        },
    )
    return folder


# ============================================================
# MAIN RESOLUTION SERVICE (ORGASSIGNMENT ONLY)
# ============================================================

@transaction.atomic
def resolve_attachment_folder(*, work_item, attachment_type, actor):
    """
    Resolves the default attachment folder using OrgAssignment
    as the single source of truth.
    """

    # -------------------------------------------------
    # 1️⃣ Permission
    # -------------------------------------------------
    assert_can_upload(work_item=work_item, actor=actor)

    # -------------------------------------------------
    # 2️⃣ OrgAssignment (REQUIRED)
    # -------------------------------------------------
    try:
        org = actor.org_assignments.select_related(
            "division",
            "section",
            "service",
            "unit",
        ).get()
    except OrgAssignment.DoesNotExist:
        raise ValidationError(
            f"User '{actor}' has no organizational assignment."
        )

    # -------------------------------------------------
    # 3️⃣ ROOT
    # -------------------------------------------------
    root = get_or_create_folder(
        name="ROOT",
        folder_type=DocumentFolder.FolderType.ROOT,
        parent=None,
    )

    # -------------------------------------------------
    # 4️⃣ YEAR
    # -------------------------------------------------
    year_folder = get_or_create_folder(
        name=str(work_item.workcycle.due_at.year),
        folder_type=DocumentFolder.FolderType.YEAR,
        parent=root,
    )

    # -------------------------------------------------
    # 5️⃣ CATEGORY (attachment bucket)
    # -------------------------------------------------
    category_folder = get_or_create_folder(
        name="Workcycles",
        folder_type=DocumentFolder.FolderType.CATEGORY,
        parent=year_folder,
    )

    # -------------------------------------------------
    # 6️⃣ WORKCYCLE
    # -------------------------------------------------
    workcycle_folder = get_or_create_folder(
        name=work_item.workcycle.title,
        folder_type=DocumentFolder.FolderType.WORKCYCLE,
        parent=category_folder,
        workcycle=work_item.workcycle,
    )

    # -------------------------------------------------
    # 7️⃣ DIVISION
    # -------------------------------------------------
    division_folder = get_or_create_folder(
        name=org.division.name,
        folder_type=DocumentFolder.FolderType.DIVISION,
        parent=workcycle_folder,
    )

    # -------------------------------------------------
    # 8️⃣ SECTION
    # -------------------------------------------------
    section_folder = get_or_create_folder(
        name=org.section.name,
        folder_type=DocumentFolder.FolderType.SECTION,
        parent=division_folder,
    )

    # -------------------------------------------------
    # 9️⃣ SERVICE (optional)
    # -------------------------------------------------
    parent_for_unit = section_folder

    if org.service:
        service_folder = get_or_create_folder(
            name=org.service.name,
            folder_type=DocumentFolder.FolderType.SERVICE,
            parent=section_folder,
        )
        parent_for_unit = service_folder

    # -------------------------------------------------
    # 🔟 UNIT (optional)
    # -------------------------------------------------
    parent_for_attachment = parent_for_unit

    if org.unit:
        unit_folder = get_or_create_folder(
            name=org.unit.name,
            folder_type=DocumentFolder.FolderType.UNIT,
            parent=parent_for_unit,
        )
        parent_for_attachment = unit_folder

    # -------------------------------------------------
    # 1️⃣1️⃣ ATTACHMENT TYPE (FINAL)
    # -------------------------------------------------
    attachment_folder = get_or_create_folder(
        name=attachment_type.upper(),
        folder_type=DocumentFolder.FolderType.ATTACHMENT,
        parent=parent_for_attachment,
    )

    return attachment_folder
