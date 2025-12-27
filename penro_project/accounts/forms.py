from django import forms
from django.core.exceptions import ValidationError

from .models import User, OrgAssignment, Team


from django import forms
from django.core.exceptions import ValidationError
from accounts.models import User


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
            "placeholder": "Min. 8 characters",
        }),
        strip=False,
    )

    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
            "placeholder": "Re-enter password",
        }),
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
        widgets = {
            "username": forms.TextInput(attrs={
                "placeholder": "e.g. john.doe",
            }),
            "first_name": forms.TextInput(attrs={
                "placeholder": "Juan",
            }),
            "last_name": forms.TextInput(attrs={
                "placeholder": "Dela Cruz",
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "email@example.com",
            }),
            "position_title": forms.TextInput(attrs={
                "placeholder": "e.g. Manager (optional)",
            }),
            "login_role": forms.Select(attrs={
                "class": "form-select",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes to all fields
        for field_name, field in self.fields.items():
            if field_name == "login_role":
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"

    # ----------------------------
    # VALIDATION
    # ----------------------------
    def clean_username(self):
        username = self.cleaned_data.get("username")
        
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken.")
        
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")
        
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        
        if email and User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        
        return email

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
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Last name"}),
            "email": forms.EmailInput(attrs={"placeholder": "email@example.com"}),
            "position_title": forms.TextInput(attrs={"placeholder": "Job title"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes to all fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"

class OrgAssignmentForm(forms.ModelForm):
    class Meta:
        model = OrgAssignment
        fields = ["user", "division", "section", "service", "unit"]

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
