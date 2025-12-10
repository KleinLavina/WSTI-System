from django.db import models
from django.contrib.auth.models import AbstractUser


class Department(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    position_title = models.CharField(max_length=150, blank=True)

    permission_role = models.CharField(
        max_length=50,
        choices=[
            ("admin", "Admin"),
            ("manager", "Manager"),
            ("user", "User"),
        ],
        default="user",
    )

    contact_number = models.CharField(max_length=20, blank=True)

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users"
    )

    def __str__(self):
        full = self.get_full_name()
        return f"{full} ({self.username})" if full else self.username
