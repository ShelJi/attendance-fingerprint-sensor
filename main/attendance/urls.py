from django.urls import path
from .views import employee_list, fingerprint_scan, employee_detail, device_status


urlpatterns = [
    path(
        "attendance/scan/",
        fingerprint_scan,
        name="fingerprint_scan",
    ),
    
    path(
        "employees/",
        employee_list,
        name="employee_list",
    ),
        
    path(
        "employees/<int:employee_id>/",
        employee_detail,
        name="employee_detail",
    ),
    
    path(
        "device/status/",
        device_status,
        name="device_status",
    ),
]
