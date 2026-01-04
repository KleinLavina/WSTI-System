from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
import re

from accounts.models import WorkItemAttachment, Team, WorkCycle
from structure.services.folder_resolution import (
    resolve_folder_context,
    acronym,
)


# =====================================================
# HELPER: WORKCYCLE ACRONYM (YEAR SAFE)
# =====================================================
def workcycle_acronym(title: str) -> str:
    """
    Acronymizes a WorkCycle title while preserving full years.

    Example:
      "Quarter 1 Operations Report 2026"
      → "Q1OR 2026"
    """
    if not title:
        return "—"

    parts = []
    for word in title.split():
        if re.fullmatch(r"\d{4}", word):
            parts.append(word)
        else:
            parts.append(acronym(word))

    return " ".join(parts)


# =====================================================
# VIEW: ALL FILES (FLAT LIST – NOT FILE MANAGER)
# =====================================================
@staff_member_required
def all_files_uploaded(request):
    """
    Admin view: list all uploaded files (FLAT VIEW).

    GUARANTEES:
    - Never redirects to File Manager
    - File URLs point to ACTUAL files (not folders)
    - Workcycle resolution is always correct
    - Org resolution is folder-based but safe
    """

    # =====================================================
    # BASE QUERYSET (FILES ONLY)
    # =====================================================
    qs = (
        WorkItemAttachment.objects
        .select_related(
            "uploaded_by",
            "work_item",
            "work_item__workcycle",
            "folder",
            "folder__workcycle",
        )
        .order_by("-uploaded_at")
    )

    # =====================================================
    # FILTER PARAMS
    # =====================================================
    year = request.GET.get("year")
    attachment_type = request.GET.get("type")
    division = request.GET.get("division")
    section = request.GET.get("section")
    service = request.GET.get("service")
    unit = request.GET.get("unit")

    # =====================================================
    # SAFE DB FILTERS (WORKCYCLE-BASED)
    # =====================================================
    if year:
        qs = qs.filter(work_item__workcycle__due_at__year=year)

    if attachment_type:
        qs = qs.filter(attachment_type=attachment_type)

    # =====================================================
    # FLATTEN FILES (NO NAVIGATION SIDE EFFECTS)
    # =====================================================
    files = []

    for attachment in qs:
        ctx = resolve_folder_context(attachment.folder)

        # -----------------------------
        # SAFE WORKCYCLE RESOLUTION
        # -----------------------------
        workcycle = (
            ctx["workcycle"]
            or getattr(attachment.work_item, "workcycle", None)
        )

        # -----------------------------
        # ORG FILTERS (POST-RESOLUTION)
        # -----------------------------
        if division and ctx["division"] != division:
            continue
        if section and ctx["section"] != section:
            continue
        if service and ctx["service"] != service:
            continue
        if unit:
            if unit == "N/A":
                if not ctx["unassigned"]:
                    continue
            elif ctx["unit"] != unit:
                continue

        files.append({
            # FILE (REAL FILE URL – NOT FILE MANAGER)
            "name": attachment.file.name.rsplit("/", 1)[-1],
            "file_url": attachment.file.url,  # ✅ MEDIA FILE URL

            # TYPE
            "type": attachment.get_attachment_type_display(),

            # WORKCYCLE (ACRONYM + YEAR)
            "workcycle": (
                workcycle_acronym(workcycle.title)
                if workcycle else "—"
            ),

            # ORG (ACRONYMS)
            "division": acronym(ctx["division"]) if ctx["division"] else "—",
            "section": acronym(ctx["section"]) if ctx["section"] else "—",
            "service": acronym(ctx["service"]) if ctx["service"] else "—",
            "unit": (
                acronym(ctx["unit"])
                if ctx["unit"]
                else ("N/A" if ctx["unassigned"] else "—")
            ),

            # META
            "uploaded_by": attachment.uploaded_by,
            "uploaded_at": attachment.uploaded_at,
        })

    # =====================================================
    # FILTER OPTIONS
    # =====================================================
    filters = {
        "years": (
            WorkCycle.objects
            .values_list("due_at__year", flat=True)
            .distinct()
            .order_by("-due_at__year")
        ),
        "attachment_types": WorkItemAttachment.ATTACHMENT_TYPE_CHOICES,
        "divisions": (
            Team.objects
            .filter(team_type=Team.TeamType.DIVISION)
            .values_list("name", flat=True)
            .order_by("name")
        ),
        "sections": (
            Team.objects
            .filter(team_type=Team.TeamType.SECTION)
            .values_list("name", flat=True)
            .order_by("name")
        ),
        "services": (
            Team.objects
            .filter(team_type=Team.TeamType.SERVICE)
            .values_list("name", flat=True)
            .order_by("name")
        ),
        "units": (
            list(
                Team.objects
                .filter(team_type=Team.TeamType.UNIT)
                .values_list("name", flat=True)
                .order_by("name")
            ) + ["N/A"]
        ),
    }

    # =====================================================
    # RENDER (FLAT VIEW ONLY)
    # =====================================================
    return render(
        request,
        "admin/page/all_files_uploaded.html",
        {
            "files": files,
            "total_files": len(files),
            "filters": filters,
            "active": {
                "year": year,
                "type": attachment_type,
                "division": division,
                "section": section,
                "service": service,
                "unit": unit,
            },
        }
    )
