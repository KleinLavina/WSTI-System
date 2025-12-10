from django.contrib import admin
from .models import Department, User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created_at")
    search_fields = ("name",)
    ordering = ("name",)


class UserAdmin(BaseUserAdmin):
    model = User
    list_display = (
        "username", "email", "first_name", "last_name",
        "department", "position_title", "permission_role",
        "is_active", "is_staff"
    )
    list_filter = ("permission_role", "department", "is_staff", "is_active")

    fieldsets = BaseUserAdmin.fieldsets + (
        ("PENRO User Details", {
            "fields": (
                "department",
                "position_title",
                "permission_role",
                "contact_number",
            )
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "first_name", "last_name",   # ✅ add here
                "email",
                "password1", "password2",

                # Custom fields
                "department",
                "position_title",
                "permission_role",
                "contact_number",
            ),
        }),
    )

    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)



admin.site.register(User, UserAdmin)
