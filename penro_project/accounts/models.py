from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class User(AbstractUser):
    position_title = models.CharField(
        max_length=150,
        blank=True,
        help_text="Job title or designation"
    )

    login_role = models.CharField(
        max_length=50,
        choices=[
            ("admin", "Admin"),
            ("manager", "Manager"),
            ("user", "User"),
        ],
        default="user",
        db_index=True,
        help_text="Defines access level inside the system"
    )

    class Meta:
        ordering = ["username"]

    def __str__(self):
        full_name = self.get_full_name()
        return f"{full_name} ({self.username})" if full_name else self.username


class Team(models.Model):
    name = models.CharField(
        max_length=150,
        unique=True,
        help_text="Team, unit, or group name"
    )

    description = models.TextField(
        blank=True,
        help_text="Optional description of the team"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="memberships"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="team_memberships"
    )

    role = models.CharField(
        max_length=30,
        choices=[
            ("lead", "Team Lead"),
            ("member", "Member"),
        ],
        default="member",
        help_text="Role of the user within the team"
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("team", "user")
        ordering = ["team__name"]

    def __str__(self):
        return f"{self.user} → {self.team} ({self.role})"


# ============================================================
# 3. PLANNING (WHAT & WHEN)
# ============================================================

class WorkCycle(models.Model):
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
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_workcycles",
        help_text="User who created this work cycle"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Inactive work cycles are archived"
    )

    created_at = models.DateTimeField(auto_now_add=True)

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

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Inactive items are archived due to reassignment"
    )

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

    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("workcycle", "owner")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["review_decision"]),
            models.Index(fields=["is_active"]),  # 👈 add this
        ]


    def __str__(self):
        return f"{self.workcycle} — {self.owner}"


class WorkItemAttachment(models.Model):
    work_item = models.ForeignKey(
        WorkItem,
        on_delete=models.CASCADE,
        related_name="attachments",
        help_text="Work item this file belongs to"
    )

    file = models.FileField(
        upload_to="work_items/",
        help_text="Uploaded file"
    )

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who uploaded the file"
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for {self.work_item}"

class WorkItemMessage(models.Model):
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

    sender_role = models.CharField(
        max_length=50,
        choices=[
            ("admin", "Admin"),
            ("manager", "Manager"),
            ("user", "User"),
        ],
        db_index=True
    )

    message = models.TextField(
        help_text="Message regarding status, review, or work clarification"
    )

    # Optional context (VERY useful)
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

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["sender_role"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.sender} → {self.work_item}"
