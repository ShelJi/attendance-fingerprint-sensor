from django import forms
from django.contrib.auth import get_user_model

from .models import Employee


class EmployeeForm(forms.ModelForm):
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
