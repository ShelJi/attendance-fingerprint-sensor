from django.shortcuts import render
from attendance.models import AttendanceSession
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Employee
from .services import process_scan
from datetime import datetime
from datetime import timedelta
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from .models import AttendanceDevice
from django.shortcuts import redirect, render
from .forms import EmployeeForm
from .models import AttendanceDevice, DeviceCommand


# ============================================================
# ATTENDANCE SCAN API (Pico → Backend)
# ============================================================

@csrf_exempt
def fingerprint_scan(request):

    if request.method != "POST":
        return JsonResponse(
            {"error": "POST required"},
            status=405,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "success": False,
                "message": "INVALID DATA",
                "error": "Invalid JSON",
            },
            status=400,
        )

    fingerprint_id = data.get("fingerprint_id")

    if not fingerprint_id:
        return JsonResponse(
            {
                "success": False,
                "message": "NO ID SENT",
                "error": "fingerprint_id required",
            },
            status=400,
        )

    employee = Employee.objects.filter(
        fingerprint_id=fingerprint_id
    ).first()

    if employee is None:
        return JsonResponse(
            {
                "success": False,
                "message": "USER NOT\nFOUND",
                "error": "Employee not found",
            },
            status=404,
        )

    session, action = process_scan(
        employee=employee,
        occurred_at=timezone.now(),
    )

    # Build display message for Pico
    short_name = employee.name[:12].upper()

    if action == "login":
        message = short_name + "\nLOGIN OK"
    elif action == "logout":
        worked = ""
        if session.worked_hours:
            total_seconds = int(
                session.worked_hours.total_seconds()
            )
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            worked = str(hours) + "H " + str(minutes) + "M"

        message = short_name + "\nLOGOUT " + worked
    elif action == "already_logged_in":
        message = short_name + "\nALREADY IN"
    elif action == "already_done":
        message = short_name + "\nWAIT A BIT"
    else:
        message = short_name + "\n" + str(action).upper()

    return JsonResponse({
        "success": True,
        "employee": employee.name,
        "employee_id": employee.employee_id,
        "action": action,
        "session_id": session.id,
        "message": message,
    })


# ============================================================
# DEVICE STATUS API (Pico → Backend)
# ============================================================

@csrf_exempt
def device_status(request):
    if request.method != "POST":
        return JsonResponse(
            {"error": "POST required"},
            status=405,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON"},
            status=400,
        )

    device_id = data.get("device_id")

    if not device_id:
        return JsonResponse(
            {"error": "device_id required"},
            status=400,
        )

    device, created = AttendanceDevice.objects.get_or_create(
        device_id=device_id
    )

    device.last_seen = timezone.now()
    device.save(
        update_fields=["last_seen"]
    )

    return JsonResponse({
        "success": True,
        "device_id": device.device_id,
        "status": "online",
        "last_seen": device.last_seen.isoformat(),
    })


# ============================================================
# DEVICE COMMAND API (Pico polls this)
# ============================================================

@csrf_exempt
def device_command(request):

    if request.method != "GET":
        return JsonResponse(
            {"error": "GET required"},
            status=405,
        )

    device_id = request.GET.get("device_id")

    if not device_id:
        return JsonResponse(
            {"error": "device_id required"},
            status=400,
        )

    device = AttendanceDevice.objects.filter(
        device_id=device_id,
        is_active=True,
    ).first()

    if device is None:
        return JsonResponse(
            {
                "success": False,
                "error": "Device not found",
            },
            status=404,
        )

    command = (
        DeviceCommand.objects
        .filter(
            device=device,
            status="pending",
        )
        .order_by("created_at")
        .first()
    )

    if command is None:
        return JsonResponse({
            "success": True,
            "command": None,
        })

    command.status = "running"
    command.save(
        update_fields=["status"]
    )

    return JsonResponse({
        "success": True,
        "command": {
            "id": command.id,
            "type": command.command,
            "fingerprint_id": command.fingerprint_id,
        },
    })


# ============================================================
# DEVICE COMMAND RESULT API (Pico → Backend)
# ============================================================

@csrf_exempt
def device_command_result(request):

    if request.method != "POST":
        return JsonResponse(
            {"error": "POST required"},
            status=405,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON"},
            status=400,
        )

    device_id = data.get("device_id")
    command_id = data.get("command_id")
    success = data.get("success")
    result = data.get("result")

    if not device_id:
        return JsonResponse(
            {"error": "device_id required"},
            status=400,
        )

    if not command_id:
        return JsonResponse(
            {"error": "command_id required"},
            status=400,
        )

    device = AttendanceDevice.objects.filter(
        device_id=device_id,
        is_active=True,
    ).first()

    if device is None:
        return JsonResponse(
            {
                "success": False,
                "error": "Device not found",
            },
            status=404,
        )

    command = DeviceCommand.objects.filter(
        id=command_id,
        device=device,
    ).first()

    if command is None:
        return JsonResponse(
            {
                "success": False,
                "error": "Command not found",
            },
            status=404,
        )

    command.status = (
        "completed"
        if success
        else "failed"
    )

    command.result = result
    command.completed_at = timezone.now()

    command.save(
        update_fields=[
            "status",
            "result",
            "completed_at",
        ]
    )

    return JsonResponse({
        "success": True,
        "message": "Command result saved",
    })


# ============================================================
# WEB VIEWS — Employee List
# ============================================================

@login_required
def employee_list(request):

    employees = Employee.objects.all().prefetch_related(
        "attendance_sessions"
    )

    employee_data = []

    for employee in employees:

        last_session = (
            employee.attendance_sessions
            .order_by("-login_at")
            .first()
        )

        if last_session is None:
            last_action = "No attendance"
            last_time = None

        elif last_session.logout_at is not None:
            last_action = "Logout"
            last_time = last_session.logout_at

        else:
            last_action = "Login"
            last_time = last_session.login_at

        employee_data.append({
            "employee": employee,
            "last_action": last_action,
            "last_time": last_time,
            "worked_hours": last_session.worked_hours if last_session else None,
        })

    return render(
        request,
        "attendance/employees.html",
        {
            "employee_data": employee_data,
        },
    )


# ============================================================
# WEB VIEWS — Employee Detail
# ============================================================

@login_required
def employee_detail(request, employee_id):
    employee = get_object_or_404(
        Employee,
        id=employee_id,
    )

    attendance = (
        employee.attendance_sessions
        .order_by("-login_at")
    )

    # Get filters
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")

    # Filter by start date
    if start_date:
        try:
            start = datetime.strptime(
                start_date,
                "%Y-%m-%d",
            ).date()

            attendance = attendance.filter(
                login_at__date__gte=start
            )
        except ValueError:
            start_date = ""

    # Filter by end date
    if end_date:
        try:
            end = datetime.strptime(
                end_date,
                "%Y-%m-%d",
            ).date()

            attendance = attendance.filter(
                login_at__date__lte=end
            )
        except ValueError:
            end_date = ""

    # Calculate total worked hours
    total_worked = attendance.aggregate(
        total=Sum("worked_hours")
    )["total"]

    if total_worked is None:
        total_worked = timedelta(0)

    # Format total worked hours
    total_seconds = int(total_worked.total_seconds())
    total_hours = total_seconds // 3600
    total_minutes = (total_seconds % 3600) // 60
    total_worked_display = f"{total_hours}h {total_minutes}m"

    # Pagination
    paginator = Paginator(
        attendance,
        10,
    )

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(
        page_number
    )

    return render(
        request,
        "attendance/employee_detail.html",
        {
            "employee": employee,
            "page_obj": page_obj,
            "start_date": start_date,
            "end_date": end_date,
            "total_worked": total_worked_display,
        },
    )


# ============================================================
# WEB VIEWS — Employee Create
# ============================================================

@login_required
def employee_create(request):

    if request.method == "POST":
        form = EmployeeForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("employee_list")

    else:
        form = EmployeeForm()

    return render(
        request,
        "attendance/employee_create.html",
        {
            "form": form,
        },
    )


# ============================================================
# WEB VIEWS — Device Control Panel
# ============================================================

@login_required
def device_control(request):
    device = AttendanceDevice.objects.filter(
        device_id="attendance-01"
    ).first()

    return render(
        request,
        "attendance/device_control.html",
        {
            "device": device,
        },
    )


# ============================================================
# WEB VIEWS — Device Control Send Command
# ============================================================

@login_required
def device_control_command(request):

    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "error": "POST required",
            },
            status=405,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid JSON",
            },
            status=400,
        )

    command = data.get("command")
    fingerprint_id = data.get("fingerprint_id")

    allowed_commands = {
        "LIST_IDS",
        "ENROLL",
        "ENROLL_AUTO",
        "DELETE",
        "REPLACE",
        "VERIFY",
        "SUMMARY",
        "INFO",
    }

    if command not in allowed_commands:
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid command",
            },
            status=400,
        )

    device = AttendanceDevice.objects.filter(
        device_id="attendance-01",
        is_active=True,
    ).first()

    if device is None:
        return JsonResponse(
            {
                "success": False,
                "error": "Device not found",
            },
            status=404,
        )

    # ---------------------------------------------------------
    # Validate fingerprint ID
    # ---------------------------------------------------------

    if command in {
        "ENROLL",
        "DELETE",
        "REPLACE",
    }:

        if fingerprint_id is None:
            return JsonResponse(
                {
                    "success": False,
                    "error": "fingerprint_id required",
                },
                status=400,
            )

        try:
            fingerprint_id = int(fingerprint_id)

        except (TypeError, ValueError):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid fingerprint ID",
                },
                status=400,
            )

        if not 1 <= fingerprint_id <= 127:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Fingerprint ID must be between 1 and 127",
                },
                status=400,
            )

    # ---------------------------------------------------------
    # Expire stale commands
    # ---------------------------------------------------------
    command_timeout = timezone.now() - timedelta(minutes=1)

    DeviceCommand.objects.filter(
        device=device,
        status__in=["pending", "running"],
        created_at__lt=command_timeout,
    ).update(
        status="failed",
        result={
            "message": "Command expired: device did not respond"
        },
        completed_at=timezone.now(),
    )

    # ---------------------------------------------------------
    # Check for existing active command
    # ---------------------------------------------------------

    active_command = (
        DeviceCommand.objects
        .filter(
            device=device,
            status__in=["pending", "running"],
        )
        .order_by("-created_at")
        .first()
    )

    if active_command:

        # Same command already exists.
        if (
            active_command.command == command
            and active_command.fingerprint_id == fingerprint_id
        ):
            return JsonResponse({
                "success": True,
                "message": "Command already exists",
                "command_id": active_command.id,
                "command": active_command.command,
                "status": active_command.status,
            })

        # Different command is already active.
        return JsonResponse(
            {
                "success": False,
                "error": "Another command is already running",
                "command_id": active_command.id,
                "command": active_command.command,
                "status": active_command.status,
            },
            status=409,
        )

    # ---------------------------------------------------------
    # Create command
    # ---------------------------------------------------------

    device_command_obj = DeviceCommand.objects.create(
        device=device,
        command=command,
        fingerprint_id=fingerprint_id,
        status="pending",
    )

    return JsonResponse({
        "success": True,
        "message": "Command queued",
        "command_id": device_command_obj.id,
        "command": command,
        "status": "pending",
    })


# ============================================================
# WEB VIEWS — Device Control Result Polling
# ============================================================

@login_required
def device_control_result(request):

    command_id = request.GET.get(
        "command_id"
    )

    if not command_id:
        return JsonResponse(
            {
                "success": False,
                "error": "command_id required",
            },
            status=400,
        )

    command = DeviceCommand.objects.filter(
        id=command_id,
    ).first()

    if command is None:
        return JsonResponse(
            {
                "success": False,
                "error": "Command not found",
            },
            status=404,
        )

    return JsonResponse({
        "success": True,
        "status": command.status,
        "result": command.result,
    })


# ============================================================
# WEB VIEWS — Dashboard
# ============================================================

@login_required
def dashboard(request):

    device = AttendanceDevice.objects.filter(
        device_id="attendance-01"
    ).first()

    # Stats
    today = timezone.localdate()
    total_employees = Employee.objects.count()
    today_sessions = AttendanceSession.objects.filter(
        login_at__date=today
    ).count()
    active_sessions = AttendanceSession.objects.filter(
        login_at__date=today,
        logout_at__isnull=True,
    ).count()

    return render(
        request,
        "attendance/dashboard.html",
        {
            "device": device,
            "total_employees": total_employees,
            "today_sessions": today_sessions,
            "active_sessions": active_sessions,
        },
    )