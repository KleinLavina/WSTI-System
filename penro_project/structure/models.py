from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class DocumentFolder(models.Model):
    class FolderType(models.TextChoices):
        ROOT = "root", "Root"
        YEAR = "year", "Year"
        CATEGORY = "category", "Category"
        WORKCYCLE = "workcycle", "Work Cycle"

        DIVISION = "division", "Division"
        SECTION = "section", "Section"
        SERVICE = "service", "Service"
        UNIT = "unit", "Unit"

        ATTACHMENT = "attachment", "Attachment"

    # ======================================================
    # FIELDS
    # ======================================================

    name = models.CharField(
        max_length=150,
        help_text="Folder display name"
    )

    folder_type = models.CharField(
        max_length=20,
        choices=FolderType.choices,
        db_index=True
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.PROTECT
    )

    workcycle = models.ForeignKey(
        "accounts.WorkCycle",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="folders"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    is_system_generated = models.BooleanField(
        default=True,
        help_text="True = system hierarchy folder, False = user-created folder"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # ======================================================
    # META
    # ======================================================

    class Meta:
        ordering = ["folder_type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "name"],
                name="unique_folder_name_per_parent"
            )
        ]
        indexes = [
            models.Index(fields=["folder_type"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["workcycle"]),
        ]

    # ======================================================
    # HELPERS
    # ======================================================

    def get_path(self):
        """
        Returns folders from ROOT → ... → self
        """
        path = []
        current = self
        while current:
            path.append(current)
            current = current.parent
        return list(reversed(path))

    def get_path_string(self):
        """
        Returns human-readable path string.
        Example: "ROOT / 2024 / MATRIX_A / Q1 Report / Engineering / Backend"
        """
        return " / ".join(folder.name for folder in self.get_path())

    # ======================================================
    # VALIDATION (SINGLE SOURCE OF TRUTH)
    # ======================================================

    def clean(self):
        """
        Enforces:
        - NEW STRUCTURE: ROOT > YEAR > CATEGORY (attachment type) > WORKCYCLE > Org hierarchy
        - Strict hierarchy for system folders
        - Flexible placement for manual folders
        - No ROOT nesting
        - No circular references
        """

        # NEW HIERARCHY STRUCTURE
        hierarchy = {
            self.FolderType.ROOT: [None],
            
            # Year comes directly under ROOT
            self.FolderType.YEAR: [self.FolderType.ROOT],
            
            # Category (attachment type buckets) under YEAR
            self.FolderType.CATEGORY: [self.FolderType.YEAR],
            
            # Workcycle under CATEGORY
            self.FolderType.WORKCYCLE: [self.FolderType.CATEGORY],
            
            # Organizational hierarchy under WORKCYCLE
            self.FolderType.DIVISION: [self.FolderType.WORKCYCLE],
            self.FolderType.SECTION: [self.FolderType.DIVISION],
            self.FolderType.SERVICE: [self.FolderType.SECTION],
            self.FolderType.UNIT: [self.FolderType.SECTION, self.FolderType.SERVICE],

            # Attachments are flexible - can be under any org level
            self.FolderType.ATTACHMENT: [
                self.FolderType.DIVISION,
                self.FolderType.SECTION,
                self.FolderType.SERVICE,
                self.FolderType.UNIT,
            ],
        }

        # ROOT rules
        if self.folder_type == self.FolderType.ROOT:
            if self.parent is not None:
                raise ValidationError("Root folder cannot have a parent.")
            return

        if not self.parent:
            raise ValidationError(
                f"{self.get_folder_type_display()} folder must have a parent."
            )

        # Prevent circular nesting (folder → itself / descendants)
        ancestor = self.parent
        while ancestor:
            if ancestor == self:
                raise ValidationError("Cannot move a folder inside itself.")
            ancestor = ancestor.parent

        # System folders → strict hierarchy
        if self.is_system_generated:
            allowed = hierarchy[self.folder_type]
            if self.parent.folder_type not in allowed:
                allowed_labels = ", ".join(
                    dict(self.FolderType.choices)[t] for t in allowed
                )
                raise ValidationError(
                    f"{self.get_folder_type_display()} folder must belong under: {allowed_labels}"
                )

        # Manual folders → flexible (but never ROOT)
        else:
            if self.parent.folder_type == self.FolderType.ROOT:
                raise ValidationError(
                    "Manual folders cannot be created directly under ROOT."
                )

        # Workcycle integrity
        if self.folder_type == self.FolderType.WORKCYCLE and not self.workcycle:
            raise ValidationError("Workcycle folder must reference a WorkCycle.")

        if self.folder_type != self.FolderType.WORKCYCLE and self.workcycle:
            raise ValidationError("Only WORKCYCLE folders may reference a WorkCycle.")

    # ======================================================
    # SAVE
    # ======================================================

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_folder_type_display()})"