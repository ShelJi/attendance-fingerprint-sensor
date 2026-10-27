from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from .models import Employee, OfficeLocation


class OfficeLocationForm(forms.ModelForm):
    wifi_ssid = forms.CharField(label="Wi-Fi network name (SSID)", max_length=32, strip=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-input"

    class Meta:
        model = OfficeLocation
        fields = ["name", "is_active", "wifi_ssid", "wifi_bssid", "latitude", "longitude", "radius_meters", "max_accuracy_meters"]
        labels = {"wifi_bssid": "Wi-Fi access-point BSSID", "radius_meters": "Allowed radius (metres)", "max_accuracy_meters": "Maximum GPS uncertainty (metres)"}

    def clean_wifi_bssid(self):
        return self.cleaned_data["wifi_bssid"].lower()


class EmployeeForm(forms.ModelForm):
    password = forms.CharField(
        required=False, strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="New employees default to 12345. Leave blank when editing to keep the current password.",
    )

    def clean_password(self):
        password = self.cleaned_data["password"]
        if password and password != "12345":
            user = self.cleaned_data.get("user") or (self.instance.user if self.instance.user_id else get_user_model()(username=self.cleaned_data.get("employee_id", "")))
            validate_password(password, user)
        return password

    def save(self, commit=True):
        with transaction.atomic():
            employee = super().save(commit=commit)
            if commit and self.cleaned_data.get("password"):
                employee.user.set_password(self.cleaned_data["password"])
                employee.user.save(update_fields=["password"])
            return employee

    def clean_employee_id(self):
        value = self.cleaned_data["employee_id"]
        if not self.instance.pk and get_user_model().objects.filter(username=value).exists():
            raise forms.ValidationError("This employee ID is already used as a username.")
        return value

    class Meta:
        model = Employee
        fields = [
            "name",
            "employee_id",
            "fingerprint_id",
            "password",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Employee name",
                }
            ),
            "employee_id": forms.TextInput(
                attrs={
                    "placeholder": "Employee ID",
                }
            ),
            "fingerprint_id": forms.TextInput(
                attrs={
                    "placeholder": "Fingerprint ID",
                }
            ),
        }
