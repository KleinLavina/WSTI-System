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

    IMPORTANT:
    - Uses (parent, name) uniqueness
    - Does NOT alter hierarchy logic
    - Ensures workcycle inheritance for org folders
    """

    folder, created = DocumentFolder.objects.get_or_create(
        parent=parent,
        name=name,
        defaults={
            "folder_type": folder_type,
            "workcycle": workcycle,
            "created_by": created_by,
            "is_system_generated": system,
        },
    )

    # --------------------------------------------------------
    # HARDEN WORKCYCLE INHERITANCE (SAFE FIX)
    # --------------------------------------------------------
    # Org folders MUST belong to the same workcycle as parent
    # This does NOT change resolution behavior — only correctness
    if (
        folder_type in {
            DocumentFolder.FolderType.DIVISION,
            DocumentFolder.FolderType.SECTION,
            DocumentFolder.FolderType.SERVICE,
            DocumentFolder.FolderType.UNIT,
        }
        and not folder.workcycle
        and parent
        and parent.workcycle
    ):
        folder.workcycle = parent.workcycle
        folder.save(update_fields=["workcycle"])

    return folder


# ============================================================
# MAIN RESOLUTION SERVICE (FLEXIBLE & GRACEFUL)
# ============================================================

@transaction.atomic
def resolve_attachment_folder(*, work_item, attachment_type, actor):
    """
    Resolves the attachment folder with flexible organizational structure.

    STRUCTURE (FIXED):
    ROOT
      └─ YEAR
          └─ CATEGORY (attachment type)
              └─ WORKCYCLE
                  └─ ORG STRUCTURE (flexible depth)

    FLEXIBILITY (UNCHANGED):
    - No org assignment → Unassigned division
    - Only division → division folder
    - Division + section → section folder
    - Service optional
    - Unit may belong to section OR service
    """

    # -------------------------------------------------
    # 1️⃣ PERMISSION CHECK
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
    # 3️⃣ YEAR (DERIVED FROM WORKCYCLE)
    # -------------------------------------------------
    year_folder = get_or_create_folder(
        name=str(work_item.workcycle.due_at.year),
        folder_type=DocumentFolder.FolderType.YEAR,
        parent=root,
    )

    # -------------------------------------------------
    # 4️⃣ CATEGORY (ATTACHMENT TYPE BUCKET)
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

    try:
        org = actor.org_assignment
    except (OrgAssignment.DoesNotExist, AttributeError):
        org = None

    # -------------------------------------------------
    # CASE 1: NO ORG ASSIGNMENT → UNASSIGNED
    # -------------------------------------------------
    if not org:
        return get_or_create_folder(
            name="Unassigned",
            folder_type=DocumentFolder.FolderType.DIVISION,
            parent=workcycle_folder,
        )

    # -------------------------------------------------
    # 7️⃣ DIVISION (ALWAYS PRESENT)
    # -------------------------------------------------
    division_folder = get_or_create_folder(
        name=org.division.name,
        folder_type=DocumentFolder.FolderType.DIVISION,
        parent=workcycle_folder,
    )

    # CASE 2: ONLY DIVISION
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

    # CASE 3: DIVISION + SECTION ONLY
    if not org.service and not org.unit:
        return section_folder

    # -------------------------------------------------
    # 9️⃣ SERVICE (OPTIONAL)
    # -------------------------------------------------
    if org.service:
        service_folder = get_or_create_folder(
            name=org.service.name,
            folder_type=DocumentFolder.FolderType.SERVICE,
            parent=section_folder,
        )

        # CASE 4: SERVICE WITHOUT UNIT
        if not org.unit:
            return service_folder

        # CASE 5: UNIT UNDER SERVICE
        return get_or_create_folder(
            name=org.unit.name,
            folder_type=DocumentFolder.FolderType.UNIT,
            parent=service_folder,
        )

    # -------------------------------------------------
    # 🔟 UNIT UNDER SECTION (NO SERVICE)
    # -------------------------------------------------
    if org.unit:
        return get_or_create_folder(
            name=org.unit.name,
            folder_type=DocumentFolder.FolderType.UNIT,
            parent=section_folder,
        )

    # Fallback (LOGICALLY UNREACHABLE)
    return section_folder


# ============================================================
# DISPLAY / CONTEXT HELPERS (READ-ONLY)
# ============================================================

def acronym(name: str | None) -> str | None:
    """
    Converts:
    'Backend Development Unit' → 'BDU'
    """
    if not name:
        return None
    return "".join(word[0].upper() for word in name.split() if word)


def resolve_folder_context(folder: DocumentFolder | None):
    """
    READ-ONLY helper.

    Safely extracts workcycle + org structure
    from ANY folder depth.

    Returns:
    {
        workcycle,
        division,
        section,
        service,
        unit,
        unassigned
    }
    """

    context = {
        "workcycle": None,
        "division": None,
        "section": None,
        "service": None,
        "unit": None,
        "unassigned": False,
    }

    if not folder:
        return context

    context["workcycle"] = folder.workcycle

    for f in folder.get_path():
        if f.folder_type == DocumentFolder.FolderType.DIVISION:
            context["division"] = f.name
            if f.name.lower() == "unassigned":
                context["unassigned"] = True

        elif f.folder_type == DocumentFolder.FolderType.SECTION:
            context["section"] = f.name

        elif f.folder_type == DocumentFolder.FolderType.SERVICE:
            context["service"] = f.name

        elif f.folder_type == DocumentFolder.FolderType.UNIT:
            context["unit"] = f.name

    return context


# ============================================================
# HELPER: UI PREVIEW (ACRONYM-BASED)
# ============================================================

def get_upload_path_preview(*, work_item, attachment_type, actor):
    """
    Returns a UI-friendly preview path using acronyms.

    Example:
    ROOT / 2024 / MATRIX_A / Q1 Report / ENG / BE / API / U1
    """

    folder = resolve_attachment_folder(
        work_item=work_item,
        attachment_type=attachment_type,
        actor=actor,
    )

    ctx = resolve_folder_context(folder)

    parts = [
        "ROOT",
        str(ctx["workcycle"].due_at.year) if ctx["workcycle"] else None,
        attachment_type.upper(),
        ctx["workcycle"].title if ctx["workcycle"] else None,
        acronym(ctx["division"]),
        acronym(ctx["section"]),
        acronym(ctx["service"]),
        acronym(ctx["unit"]) if ctx["unit"] else (
            "UNASSIGNED" if ctx["unassigned"] else None
        ),
    ]

    return " / ".join(p for p in parts if p)
