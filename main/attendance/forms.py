from django import forms

from .models import Employee


class EmployeeForm(forms.ModelForm):
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