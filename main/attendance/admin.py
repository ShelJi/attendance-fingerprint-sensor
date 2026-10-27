from django.contrib import admin
from django.core.exceptions import PermissionDenied
from .forms import EmployeeForm

from .models import Employee, AttendanceSession, AttendanceDevice, DeviceCommand
from .models import OfficeLocation, AttendanceEvidence, AttendanceNotification


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "name", "user", "fingerprint_id")
    search_fields = ("employee_id", "name", "user__username", "fingerprint_id")

    def get_form(self, request, obj=None, **kwargs):
        kwargs["form"] = EmployeeForm
        kwargs["fields"] = ("name", "employee_id", "fingerprint_id", "password") if obj is None else ("user", "name", "employee_id", "fingerprint_id", "password")
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get("password") and obj.user_id and (obj.user.is_staff or obj.user.is_superuser) and not request.user.is_superuser:
            raise PermissionDenied("Only a superuser can reset a privileged account's password.")
        form.save()


admin.site.register(AttendanceSession)
admin.site.register(AttendanceDevice)
admin.site.register(DeviceCommand)
admin.site.register(AttendanceNotification)


@admin.register(OfficeLocation)
class OfficeLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "wifi_ssid", "wifi_bssid", "radius_meters", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "wifi_ssid", "wifi_bssid")


@admin.register(AttendanceEvidence)
class AttendanceEvidenceAdmin(admin.ModelAdmin):
    list_display = ("employee", "action", "mode", "office", "place_name", "created_at")
    list_filter = ("mode", "action", "created_at", "office")
    search_fields = ("session__employee__name", "session__employee__employee_id", "place_name", "work_description")
    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ("created_at",)
        return tuple(field.name for field in AttendanceEvidence._meta.fields)

    def employee(self, obj):
        return obj.session.employee

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


