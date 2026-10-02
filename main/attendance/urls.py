from django.urls import path

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
)


urlpatterns = [

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
]