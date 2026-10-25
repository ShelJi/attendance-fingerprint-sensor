from django.contrib import admin

from .models import Employee, AttendanceSession, AttendanceDevice, DeviceCommand
from .models import OfficeLocation, AttendanceEvidence


admin.site.register(Employee)   
admin.site.register(AttendanceSession)
admin.site.register(AttendanceDevice)
admin.site.register(DeviceCommand)


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
    readonly_fields = tuple(field.name for field in AttendanceEvidence._meta.fields)

    def employee(self, obj):
        return obj.session.employee

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


