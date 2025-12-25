from django import forms
from django.core.exceptions import ValidationError

from .models import User, OrgAssignment, Team


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
    )

    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "position_title",
            "login_role",
        ]

    # ----------------------------
    # VALIDATION
    # ----------------------------
    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")

        if not password or not confirm:
            raise ValidationError("Password and confirm password are required.")

        if password != confirm:
            raise ValidationError("Passwords do not match.")

        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")

        return cleaned_data

    # ----------------------------
    # SAVE
    # ----------------------------
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])  # ✅ proper hashing

        if commit:
            user.save()

        return user

       
       
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "position_title",
            "login_role",
            "is_active",
        ]

class OrgAssignmentForm(forms.ModelForm):
    class Meta:
        model = OrgAssignment
        fields = ["division", "section", "service", "unit"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ----------------------------
        # Default: empty dependent fields
        # ----------------------------
        self.fields["section"].queryset = Team.objects.none()
        self.fields["service"].queryset = Team.objects.none()
        self.fields["unit"].queryset = Team.objects.none()

        # ----------------------------
        # DIVISION → SECTION
        # ----------------------------
        if "division" in self.data:
            try:
                division_id = int(self.data.get("division"))
                self.fields["section"].queryset = Team.objects.filter(
                    team_type=Team.TeamType.SECTION,
                    parent_id=division_id,
                )
            except (ValueError, TypeError):
                pass

        elif self.instance.pk:
            self.fields["section"].queryset = Team.objects.filter(
                team_type=Team.TeamType.SECTION,
                parent=self.instance.division,
            )

        # ----------------------------
        # SECTION → SERVICE
        # ----------------------------
        if "section" in self.data:
            try:
                section_id = int(self.data.get("section"))
                self.fields["service"].queryset = Team.objects.filter(
                    team_type=Team.TeamType.SERVICE,
                    parent_id=section_id,
                )
            except (ValueError, TypeError):
                pass

        elif self.instance.pk and self.instance.section:
            self.fields["service"].queryset = Team.objects.filter(
                team_type=Team.TeamType.SERVICE,
                parent=self.instance.section,
            )

        # ----------------------------
        # SERVICE / SECTION → UNIT
        # ----------------------------
        if "service" in self.data or "section" in self.data:
            parents = []

            if self.data.get("section"):
                parents.append(self.data.get("section"))

            if self.data.get("service"):
                parents.append(self.data.get("service"))

            self.fields["unit"].queryset = Team.objects.filter(
                team_type=Team.TeamType.UNIT,
                parent_id__in=parents,
            )

        elif self.instance.pk:
            parents = [self.instance.section_id]
            if self.instance.service:
                parents.append(self.instance.service_id)

            self.fields["unit"].queryset = Team.objects.filter(
                team_type=Team.TeamType.UNIT,
                parent_id__in=parents,
            )
