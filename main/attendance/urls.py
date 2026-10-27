from django.urls import path
from .activity import work_attendance
from .configuration import app_configuration

from .views import (
    device_command,
    device_command_result,
    device_control,
    device_control_command,
    device_status,
    employee_create,
    employee_detail,
    employee_list,
    fingerprint_scan,
    dashboard,
    device_control_result,
    attendance_report,
    attendance_report_pdf,
    calendar_view,
    calendar_day_data,
)


urlpatterns = [
    path("configuration/", app_configuration, name="app_configuration"),
    path("configuration/<int:office_id>/", app_configuration, name="app_configuration_edit"),
    path("work-attendance/", work_attendance, name="work_attendance"),

    # =========================
    # ATTENDANCE API
    # =========================

    path(
        "attendance/scan/",
        fingerprint_scan,
        name="fingerprint_scan",
    ),


    # =========================
    # EMPLOYEES
    # =========================

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
        "employees/create/",
        employee_create,
        name="employee_create",
    ),


    # =========================
    # DEVICE
    # =========================

    path(
        "device/status/",
        device_status,
        name="device_status",
    ),

    path(
        "device/command/",
        device_command,
        name="device_command",
    ),

    path(
        "device/command/result/",
        device_command_result,
        name="device_command_result",
    ),


    # =========================
    # WEB DEVICE CONTROL
    # =========================

    path(
        "device/control/",
        device_control,
        name="device_control",
    ),

    path(
        "device/control/command/",
        device_control_command,
        name="device_control_command",
    ),


    # =========================
    # DASHBOARD
    # =========================

    path(
        "dashboard/",
        dashboard,
        name="dashboard",
    ),
    path(
        "device/control/result/",
        device_control_result,
        name="device_control_result",
    ),
    
    path(
        "calendar/",
        calendar_view,
        name="calendar",
    ),

    path(
        "calendar/day/",
        calendar_day_data,
        name="calendar_day_data",
    ),
    
    path(
        "report/",
        attendance_report,
        name="attendance_report",
    ),

    path(
        "report/pdf/",
        attendance_report_pdf,
        name="attendance_report_pdf",
    ),

]
