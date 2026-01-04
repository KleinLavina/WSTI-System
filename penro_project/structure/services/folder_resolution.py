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
    """
    Creates or retrieves a folder with the given parameters.
    Uses get_or_create to avoid duplicates.
    """
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
# MAIN RESOLUTION SERVICE (FLEXIBLE & GRACEFUL)
# ============================================================

@transaction.atomic
def resolve_attachment_folder(*, work_item, attachment_type, actor):
    """
    Resolves the attachment folder with flexible organizational structure.
    
    NEW STRUCTURE:
    ROOT > YEAR > CATEGORY (attachment type) > WORKCYCLE > Org hierarchy
    
    FLEXIBILITY:
    - No org assignment → creates "Unassigned" division
    - Only division → file goes in division folder
    - Division + section → file goes in section folder
    - Full hierarchy → file goes in deepest available level
    
    Returns: The deepest folder where the file should be placed
    """

    # -------------------------------------------------
    # 1️⃣ Permission Check
    # -------------------------------------------------
    assert_can_upload(work_item=work_item, actor=actor)

    # -------------------------------------------------
    # 2️⃣ ROOT
    # -------------------------------------------------
    root = get_or_create_folder(
        name="ROOT",
        folder_type=DocumentFolder.FolderType.ROOT,
        parent=None,
    )

    # -------------------------------------------------
    # 3️⃣ YEAR (from work cycle deadline)
    # -------------------------------------------------
    year_folder = get_or_create_folder(
        name=str(work_item.workcycle.due_at.year),
        folder_type=DocumentFolder.FolderType.YEAR,
        parent=root,
    )

    # -------------------------------------------------
    # 4️⃣ CATEGORY = Attachment Type Bucket
    # -------------------------------------------------
    attachment_type_folder = get_or_create_folder(
        name=attachment_type.upper(),  # MATRIX_A, MATRIX_B, MOV
        folder_type=DocumentFolder.FolderType.CATEGORY,
        parent=year_folder,
    )

    # -------------------------------------------------
    # 5️⃣ WORKCYCLE
    # -------------------------------------------------
    workcycle_folder = get_or_create_folder(
        name=work_item.workcycle.title,
        folder_type=DocumentFolder.FolderType.WORKCYCLE,
        parent=attachment_type_folder,
        workcycle=work_item.workcycle,
    )

    # -------------------------------------------------
    # 6️⃣ ORGANIZATIONAL STRUCTURE (FLEXIBLE)
    # -------------------------------------------------
    
    # Try to get user's org assignment
    try:
        org = actor.org_assignment
    except (OrgAssignment.DoesNotExist, AttributeError):
        org = None

    # CASE 1: No org assignment → create "Unassigned" bucket
    if not org:
        unassigned_folder = get_or_create_folder(
            name="Unassigned",
            folder_type=DocumentFolder.FolderType.DIVISION,
            parent=workcycle_folder,
        )
        return unassigned_folder

    # -------------------------------------------------
    # 7️⃣ DIVISION (always present if org exists)
    # -------------------------------------------------
    division_folder = get_or_create_folder(
        name=org.division.name,
        folder_type=DocumentFolder.FolderType.DIVISION,
        parent=workcycle_folder,
    )

    # CASE 2: Only division → file goes here
    if not org.section:
        return division_folder

    # -------------------------------------------------
    # 8️⃣ SECTION
    # -------------------------------------------------
    section_folder = get_or_create_folder(
        name=org.section.name,
        folder_type=DocumentFolder.FolderType.SECTION,
        parent=division_folder,
    )

    # CASE 3: Division + section only → file goes here
    if not org.service and not org.unit:
        return section_folder

    # -------------------------------------------------
    # 9️⃣ SERVICE (optional branch)
    # -------------------------------------------------
    if org.service:
        service_folder = get_or_create_folder(
            name=org.service.name,
            folder_type=DocumentFolder.FolderType.SERVICE,
            parent=section_folder,
        )

        # CASE 4: Division + section + service (no unit) → file goes here
        if not org.unit:
            return service_folder

        # CASE 5: Full hierarchy with service → unit under service
        unit_folder = get_or_create_folder(
            name=org.unit.name,
            folder_type=DocumentFolder.FolderType.UNIT,
            parent=service_folder,
        )
        return unit_folder

    # -------------------------------------------------
    # 🔟 UNIT (belongs to section if no service)
    # -------------------------------------------------
    if org.unit:
        # CASE 6: Division + section + unit (no service) → unit under section
        unit_folder = get_or_create_folder(
            name=org.unit.name,
            folder_type=DocumentFolder.FolderType.UNIT,
            parent=section_folder,
        )
        return unit_folder

    # Fallback (should never reach here based on logic above)
    return section_folder


# ============================================================
# HELPER: Preview Upload Path
# ============================================================

def get_upload_path_preview(*, work_item, attachment_type, actor):
    """
    Returns a human-readable path string showing where files will be uploaded.
    Useful for UI display before actual upload.
    
    Example: "ROOT / 2024 / MATRIX_A / Q1 Report / Engineering / Backend Team"
    """
    folder = resolve_attachment_folder(
        work_item=work_item,
        attachment_type=attachment_type,
        actor=actor
    )
    return folder.get_path_string()