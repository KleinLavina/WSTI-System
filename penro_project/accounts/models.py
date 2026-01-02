from django.utils import timezone
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

from structure.models import DocumentFolder
from django.core.exceptions import ValidationError, PermissionDenied

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # =====================================================
    # BASIC USER INFO
    # =====================================================
    position_title = models.CharField(
        max_length=150,
        blank=True,
        help_text="Job title or designation"
    )

    login_role = models.CharField(
        max_length=50,
        choices=[
            ("admin", "Admin"),
            ("user", "User"),
        ],
        default="user",
        db_index=True,
    )

    # =====================================================
    # ORG ACCESSORS (SAFE & FAST)
    # =====================================================

    @property
    def primary_org(self):
        """
        Single source of truth.
        Returns OrgAssignment or None.
        """
        return getattr(self, "org_assignment", None)

    @property
    def division(self):
        return self.primary_org.division if self.primary_org else None

    @property
    def section(self):
        return self.primary_org.section if self.primary_org else None

    @property
    def service(self):
        return self.primary_org.service if self.primary_org else None

    @property
    def unit(self):
        return self.primary_org.unit if self.primary_org else None

    class Meta:
        ordering = ["username"]

    def __str__(self):
        full_name = self.get_full_name()
        return full_name or self.username


class Team(models.Model):
    class TeamType(models.TextChoices):
        DIVISION = "division", "Division"
        SECTION = "section", "Section"
        SERVICE = "service", "Service"
        UNIT = "unit", "Unit"

    name = models.CharField(max_length=150)

    team_type = models.CharField(
        max_length=20,
        choices=TeamType.choices,
        db_index=True
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children"
    )

    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["team_type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "name"],
                name="unique_team_name_per_parent"
            )
        ]

    def clean(self):
        allowed_parents = {
            self.TeamType.DIVISION: [None],
            self.TeamType.SECTION: [self.TeamType.DIVISION],
            self.TeamType.SERVICE: [self.TeamType.SECTION],
            self.TeamType.UNIT: [self.TeamType.SECTION, self.TeamType.SERVICE],
        }

        # Division must be root
        if self.team_type == self.TeamType.DIVISION:
            if self.parent is not None:
                raise ValidationError("Division cannot have a parent.")
            return

        # All others must have a parent
        if not self.parent:
            raise ValidationError("This team must have a parent.")

        if self.parent.team_type not in allowed_parents[self.team_type]:
            raise ValidationError(
                f"{self.get_team_type_display()} must belong to a valid parent."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_team_type_display()})"


class OrgAssignment(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="org_assignment"
    )

    division = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="division_assignments",
        limit_choices_to={"team_type": "division"}
    )

    section = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="section_assignments",
        limit_choices_to={"team_type": "section"}
    )

    service = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="service_assignments",
        limit_choices_to={"team_type": "service"}
    )

    unit = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="unit_assignments",
        limit_choices_to={"team_type": "unit"}
    )

    def clean(self):
        # Section must belong to Division
        if self.section.parent_id != self.division_id:
            raise ValidationError("Section must belong to Division.")

        # Service (optional) must belong to Section
        if self.service and self.service.parent_id != self.section_id:
            raise ValidationError("Service must belong to Section.")

        # Unit must belong to Section OR Service
        if self.unit:
            valid_parents = {self.section_id}
            if self.service:
                valid_parents.add(self.service_id)

            if self.unit.parent_id not in valid_parents:
                raise ValidationError(
                    "Unit must belong to Section or Service."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                name="one_org_assignment_per_user"
            )
        ]

    def __str__(self):
        return (
            f"{self.user} → "
            f"{self.division} / {self.section}"
        )

# ============================================================
# 3. PLANNING (WHAT & WHEN)
# ============================================================

class WorkCycle(models.Model):
    """
    Represents a planning window for work items.

    Lifecycle is DERIVED from:
    - Admin intent (is_active)
    - Deadline proximity (due_at)

    No lifecycle state is stored in the database.
    """

    # ============================
    # LIFECYCLE STATES (DERIVED)
    # ============================
    class LifecycleState(models.TextChoices):
        ONGOING = "ongoing", "Ongoing"
        DUE_SOON = "due_soon", "Due Soon"
        LAPSED = "lapsed", "Lapsed"
        ARCHIVED = "archived", "Archived"

    # ============================
    # CORE FIELDS
    # ============================
    title = models.CharField(
        max_length=200,
        help_text="Title of the task, report, or work cycle"
    )

    description = models.TextField(
        blank=True,
        help_text="Optional details or instructions"
    )

    due_at = models.DateTimeField(
        help_text="Deadline for this work cycle"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_workcycles",
        help_text="User who created this work cycle"
    )

    # Admin intent
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive work cycles are hidden / archived manually"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # ============================
    # DERIVED LIFECYCLE (SOURCE OF TRUTH)
    # ============================
    @property
    def lifecycle_state(self):
        """
        Determines lifecycle based on:
        1. Admin intent (is_active)
        2. Deadline proximity
        """

        # Admin override always wins
        if not self.is_active:
            return self.LifecycleState.ARCHIVED

        now = timezone.now()

        # Deadline reached or passed
        if now >= self.due_at:
            return self.LifecycleState.LAPSED

        # Due soon = within 3 days
        if (self.due_at - now) <= timedelta(days=3):
            return self.LifecycleState.DUE_SOON

        return self.LifecycleState.ONGOING

    # ============================
    # HUMAN-READABLE TIME REMAINING
    # ============================
    @property
    def time_remaining(self):
        """
        Returns remaining time in a compact human format.
        Example: '2d 4h 15m'
        """

        now = timezone.now()
        total_seconds = int((self.due_at - now).total_seconds())

        if total_seconds <= 0:
            return "Expired"

        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        parts = []
        if days:
            parts.append(f"{days}d")
        if hours or days:
            parts.append(f"{hours}h")
        if minutes or hours or days:
            parts.append(f"{minutes}m")

        return " ".join(parts)

    # ============================
    # DJANGO META
    # ============================
    class Meta:
        ordering = ["-due_at"]
        indexes = [
            models.Index(fields=["due_at"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.title
    
class WorkAssignment(models.Model):
    workcycle = models.ForeignKey(
        WorkCycle,
        on_delete=models.CASCADE,
        related_name="assignments",
        help_text="Work cycle being assigned"
    )

    assigned_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="user_assignments",
        help_text="Assign directly to a specific user"
    )

    assigned_team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="team_assignments",
        help_text="Assign to a team"
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(assigned_user__isnull=False) |
                    models.Q(assigned_team__isnull=False)
                ),
                name="workassignment_requires_user_or_team"
            )
        ]
        ordering = ["-assigned_at"]

    def __str__(self):
        target = self.assigned_user or self.assigned_team
        return f"{self.workcycle} → {target}"

# ============================================================
# 4. EXECUTION (THE WORK)
# ============================================================



class WorkItem(models.Model):
    workcycle = models.ForeignKey(
        WorkCycle,
        on_delete=models.CASCADE,
        related_name="work_items"
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="work_items"
    )

    # ======================
    # ACTIVITY / LIFECYCLE
    # ======================
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Inactive items are archived or closed for a specific reason"
    )

    inactive_reason = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        choices=[
            ("reassigned", "Reassigned"),
            ("duplicate", "Duplicate Submission"),
            ("invalid", "Invalid / Not Required"),
            ("superseded", "Superseded by New Submission"),
            ("archived", "Archived After Completion"),
        ],
        help_text="Reason why this work item became inactive"
    )

    inactive_note = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional explanation or comment"
    )

    inactive_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this item became inactive"
    )

    # ======================
    # STATUS / SUBMISSION
    # ======================
    status = models.CharField(
        max_length=30,
        choices=[
            ("not_started", "Not Started"),
            ("working_on_it", "Working on It"),
            ("done", "Done (Submitted)"),
        ],
        default="not_started",
        db_index=True
    )

    status_label = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)

    # ======================
    # REVIEW
    # ======================
    review_decision = models.CharField(
        max_length=30,
        choices=[
            ("pending", "Pending Review"),
            ("approved", "Approved"),
            ("revision", "Needs Revision"),
        ],
        default="pending",
        db_index=True
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this item was reviewed (approved or revised)"
    )

    # ======================
    # TIMESTAMPS
    # ======================
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when work was submitted"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("workcycle", "owner")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["review_decision"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["inactive_reason"]),
        ]

    # =====================================================
    # SAVE LOGIC (SAFE + AUDITABLE)
    # =====================================================
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_review = None

        if not is_new:
            old_review = (
                WorkItem.objects
                .filter(pk=self.pk)
                .values_list("review_decision", flat=True)
                .first()
            )

        # ---------------------
        # SUBMISSION TIMESTAMP
        # ---------------------
        if self.status == "done":
            if self.submitted_at is None:
                self.submitted_at = timezone.now()
        else:
            self.submitted_at = None

        # ---------------------
        # REVIEW TIMESTAMP
        # ---------------------
        if self.review_decision in ("approved", "revision"):
            if old_review != self.review_decision:
                self.reviewed_at = timezone.now()
        else:
            # reverted to pending
            self.reviewed_at = None

        # ---------------------
        # INACTIVE TIMESTAMP
        # ---------------------
        if not self.is_active:
            if self.inactive_at is None:
                self.inactive_at = timezone.now()
        else:
            self.inactive_at = None
            self.inactive_reason = ""
            self.inactive_note = ""

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.workcycle} — {self.owner}"


class WorkItemAttachment(models.Model):
    ATTACHMENT_TYPE_CHOICES = [
        ("matrix_a", "Matrix A"),
        ("matrix_b", "Matrix B"),
        ("mov", "MOV"),
    ]

    work_item = models.ForeignKey(
        WorkItem,
        on_delete=models.CASCADE,
        related_name="attachments"
    )

    folder = models.ForeignKey(
        DocumentFolder,
        null=True,
        blank=True,
        related_name="files",
        on_delete=models.SET_NULL
    )

    attachment_type = models.CharField(
        max_length=20,
        choices=ATTACHMENT_TYPE_CHOICES,
        db_index=True
    )

    file = models.FileField(upload_to="work_items/")

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="Uploader (null only for system/admin actions)"
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["attachment_type"]),
            models.Index(fields=["folder"]),
            models.Index(fields=["work_item", "folder"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["folder", "file"],
                name="unique_file_per_folder"
            )
        ]

    # ============================
    # VALIDATION
    # ============================
    def clean(self):
        if not self.folder:
            return  # Allow null folder (unorganized files)

        # Files CANNOT be placed in structural/organizational folders
        invalid_folder_types = [
            DocumentFolder.FolderType.ROOT,
            DocumentFolder.FolderType.YEAR,
            DocumentFolder.FolderType.CATEGORY,
        ]

        if self.folder.folder_type in invalid_folder_types:
            folder_label = self.folder.get_folder_type_display()
            raise ValidationError(
                f"Files cannot be placed in {folder_label} folders. "
                f"Please move them to a Workcycle, organizational unit, or attachment folder."
            )

        # Files CAN be placed in these folder types:
        # - WORKCYCLE
        # - DIVISION, SECTION, SERVICE, UNIT (org structure)
        # - ATTACHMENT (default file containers)
        
        valid_folder_types = [
            DocumentFolder.FolderType.WORKCYCLE,
            DocumentFolder.FolderType.DIVISION,
            DocumentFolder.FolderType.SECTION,
            DocumentFolder.FolderType.SERVICE,
            DocumentFolder.FolderType.UNIT,
            DocumentFolder.FolderType.ATTACHMENT,
        ]

        if self.folder.folder_type not in valid_folder_types:
            raise ValidationError(
                f"Files cannot be placed in {self.folder.get_folder_type_display()} folders."
            )

        # Workcycle integrity check
        # If the folder belongs to a specific workcycle, 
        # the file's work_item must also belong to that workcycle
        if self.folder.workcycle:
            if self.folder.workcycle != self.work_item.workcycle:
                raise ValidationError(
                    f"This folder belongs to '{self.folder.workcycle.title}' but the file "
                    f"belongs to work item in '{self.work_item.workcycle.title}'. "
                    f"Files can only be placed in folders from the same work cycle."
                )

    # ============================
    # SAVE HOOK
    # ============================
    def save(self, *args, **kwargs):
        # Auto-resolve folder if missing (on initial upload)
        if not self.folder:
            if not self.uploaded_by:
                raise PermissionDenied(
                    "uploaded_by must be set when creating attachments."
                )

            from structure.services.folder_resolution import resolve_attachment_folder

            self.folder = resolve_attachment_folder(
                work_item=self.work_item,
                attachment_type=self.attachment_type,
                actor=self.uploaded_by
            )

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_attachment_type_display()} — {self.work_item}"
    
class WorkItemMessage(models.Model):
    # ============================================================
    # RELATIONSHIPS
    # ============================================================
    work_item = models.ForeignKey(
        WorkItem,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="work_item_messages"
    )

    # ============================================================
    # MESSAGE META
    # ============================================================
    sender_role = models.CharField(
        max_length=50,
        choices=[
            ("admin", "Admin"),
            ("user", "User"),
        ],
        db_index=True,
        help_text="Role of the sender at the time the message was sent"
    )

    message = models.TextField(
        help_text="Message regarding status, review, or work clarification"
    )

    # ============================================================
    # OPTIONAL CONTEXT (SYSTEM / AUDIT MESSAGES)
    # ============================================================
    related_status = models.CharField(
        max_length=30,
        blank=True,
        help_text="Status this message refers to (optional)"
    )

    related_review = models.CharField(
        max_length=30,
        blank=True,
        help_text="Review decision this message refers to (optional)"
    )

    # ============================================================
    # READ / SEEN STATE
    # ============================================================
    is_read = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this message has been read by the other party"
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the message was read"
    )

    # ============================================================
    # TIMESTAMPS
    # ============================================================
    created_at = models.DateTimeField(auto_now_add=True)

    # ============================================================
    # MODEL CONFIG
    # ============================================================
    class Meta:
        ordering = ["created_at", "id"]  # Stable ordering
        indexes = [
            models.Index(fields=["sender_role"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_read"]),
            models.Index(fields=["work_item", "is_read"]),
        ]

    # ============================================================
    # SAVE OVERRIDE (LOCK ROLE AT CREATION)
    # ============================================================
    def save(self, *args, **kwargs):
        """
        Lock sender_role at creation time to prevent
        historical inconsistencies if user role changes.
        """
        if not self.pk and not self.sender_role:
            self.sender_role = getattr(self.sender, "login_role", "user")
        super().save(*args, **kwargs)

    # ============================================================
    # STRING REPRESENTATION
    # ============================================================
    def __str__(self):
        return (
            f"[{self.created_at:%Y-%m-%d %H:%M}] "
            f"{self.sender} → WorkItem#{self.work_item_id} "
            f"({'read' if self.is_read else 'unread'})"
        )

    # ============================================================
    # INSTANCE HELPERS
    # ============================================================
    def mark_as_read(self):
        """Mark this message as read safely."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    def is_system_message(self):
        """Detect system-generated messages (status/review updates)."""
        return bool(self.related_status or self.related_review)

    # ============================================================
    # BULK HELPERS (VERY IMPORTANT FOR INBOX UX)
    # ============================================================
    @classmethod
    def mark_thread_as_read(cls, work_item, reader):
        """
        Mark all unread messages in a work item thread
        as read for the given reader.
        """
        return cls.objects.filter(
            work_item=work_item,
            is_read=False
        ).exclude(
            sender=reader
        ).update(
            is_read=True,
            read_at=timezone.now()
        )