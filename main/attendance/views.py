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
from .decorators import management_required as login_required
from .models import AttendanceDevice
from django.shortcuts import redirect, render
from .forms import EmployeeForm
from .models import AttendanceDevice, DeviceCommand


from collections import defaultdict
from datetime import datetime, timedelta
from io import BytesIO

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)

from .models import Employee, AttendanceSession
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate
from io import BytesIO



# Preserve the HTML views while allowing mobile routes to serialize their context.
from .mobile_render import render

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
        repeat_checkout=True,
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

        message = short_name + "\nCHECKED OUT " + worked
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
   
   
   
   
   
      
def calculate_session_seconds(session, calculation_date, now):
    login_at = session.login_at
    logout_at = session.logout_at

    # Invalid/future login
    if login_at is None or login_at > now:
        return 0

    # No logout = 0 working hours
    if logout_at is None:
        return 0

    # Logout must be on the same calendar day
    login_date = timezone.localtime(login_at).date()
    logout_date = timezone.localtime(logout_at).date()

    if logout_date != login_date:
        return 0

    # Invalid logout
    if logout_at <= login_at:
        return 0

    # End of login day
    local_login = timezone.localtime(login_at)

    day_end = local_login.replace(
        hour=23,
        minute=59,
        second=59,
        microsecond=999999,
    )

    calculation_end = min(
        logout_at,
        day_end,
    )

    seconds = (
        calculation_end - login_at
    ).total_seconds()

    return max(0, int(seconds))






@login_required
def calendar_view(request):

    today = timezone.localdate()

    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))

        if month < 1 or month > 12:
            raise ValueError

    except (ValueError, TypeError):
        year = today.year
        month = today.month

    # First day of selected month
    start_date = datetime(
        year,
        month,
        1,
    ).date()

    # First day of next month
    if month == 12:
        end_date = datetime(
            year + 1,
            1,
            1,
        ).date()
    else:
        end_date = datetime(
            year,
            month + 1,
            1,
        ).date()

    sessions = (
        AttendanceSession.objects
        .filter(
            login_at__date__gte=start_date,
            login_at__date__lt=end_date,
        )
        .select_related("employee")
        .order_by("login_at")
    )

    # ---------------------------------------------------------
    # GROUP BY DATE + EMPLOYEE
    # ---------------------------------------------------------

    daily_data = {}

    now = timezone.now()

    for session in sessions:

        date_key = timezone.localtime(
            session.login_at
        ).date().isoformat()

        employee_id = session.employee.id

        key = (
            date_key,
            employee_id,
        )

        if key not in daily_data:
            daily_data[key] = {
                "date": date_key,
                "employee": session.employee,
                "login_at": session.login_at,
                "logout_at": session.logout_at,
                "worked_seconds": 0,
                "is_active": False,
            }

        item = daily_data[key]

        # Earliest login
        if session.login_at < item["login_at"]:
            item["login_at"] = session.login_at

        # Latest logout
        if session.logout_at:

            login_date = timezone.localtime(
                session.login_at
            ).date()

            logout_date = timezone.localtime(
                session.logout_at
            ).date()

            if logout_date == login_date:
                if (
                    item["logout_at"] is None
                    or session.logout_at > item["logout_at"]
                ):
                    item["logout_at"] = session.logout_at

            else:
                # Cross-midnight logout = still active
                item["is_active"] = True
                item["logout_at"] = None

        else:
            item["is_active"] = True
            item["logout_at"] = None

        # Calculate using ONE consistent rule
        item["worked_seconds"] += calculate_session_seconds(
            session,
            date_key,
            now,
        )

    # ---------------------------------------------------------
    # GROUP BY DATE
    # ---------------------------------------------------------

    calendar_data = {}

    for item in daily_data.values():

        date_key = item["date"]

        if date_key not in calendar_data:

            calendar_data[date_key] = {
                "date": date_key,
                "employee_ids": set(),
                "total_worked_seconds": 0,
            }

        calendar_data[date_key]["employee_ids"].add(
            item["employee"].id
        )

        calendar_data[date_key][
            "total_worked_seconds"
        ] += item["worked_seconds"]

    # ---------------------------------------------------------
    # CONVERT SET TO COUNT
    # ---------------------------------------------------------

    calendar_days = []

    for item in calendar_data.values():

        calendar_days.append({
            "date": item["date"],

            "employee_count": len(
                item["employee_ids"]
            ),

            "total_worked_seconds": (
                item["total_worked_seconds"]
            ),
        })

    return render(
        request,
        "attendance/calendar.html",
        {
            "year": year,
            "month": month,
            "calendar_days": json.dumps(
                calendar_days
            ),
        },
    )




@login_required
def calendar_day_data(request):

    date_string = request.GET.get("date")

    if not date_string:
        return JsonResponse(
            {
                "success": False,
                "error": "Date is required.",
            },
            status=400,
        )

    try:
        selected_date = datetime.strptime(
            date_string,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid date format. Use YYYY-MM-DD.",
            },
            status=400,
        )

    sessions = (
        AttendanceSession.objects
        .filter(
            login_at__date=selected_date,
        )
        .select_related("employee")
        .order_by(
            "employee__name",
            "login_at",
        )
    )

    now = timezone.now()

    # ---------------------------------------------------------
    # GROUP BY EMPLOYEE
    # ---------------------------------------------------------

    employee_data = {}

    for session in sessions:

        employee_id = session.employee.id

        if employee_id not in employee_data:

            employee_data[employee_id] = {
                "employee_id": employee_id,
                "employee_code": (
                    session.employee.employee_id
                ),
                "name": session.employee.name,
                "login_at": session.login_at,
                "logout_at": None,
                "worked_intervals": [],
                "is_active": False,
            }

        item = employee_data[employee_id]

        # Earliest login
        if session.login_at < item["login_at"]:
            item["login_at"] = session.login_at

        # Latest logout
        if session.logout_at:

            login_date = timezone.localtime(
                session.login_at
            ).date()

            logout_date = timezone.localtime(
                session.logout_at
            ).date()

            if logout_date == login_date:
                if (
                    item["logout_at"] is None
                    or session.logout_at > item["logout_at"]
                ):
                    item["logout_at"] = session.logout_at

            else:
                # Cross-midnight logout = still active
                item["is_active"] = True
                item["logout_at"] = None

        else:
            item["is_active"] = True
            item["logout_at"] = None

        # -----------------------------------------------------
        # BUILD ACTUAL WORK INTERVAL
        # -----------------------------------------------------

        login_at = session.login_at

        if login_at is None or login_at > now:
            continue

        local_login = timezone.localtime(login_at)

        day_start = local_login.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        day_end = local_login.replace(
            hour=23,
            minute=59,
            second=59,
            microsecond=999999,
        )

        if session.logout_at:

            logout_at = session.logout_at

            # -------------------------------------------------
            # LOGOUT MUST BE ON THE SAME CALENDAR DAY
            # -------------------------------------------------

            login_date = timezone.localtime(
                login_at
            ).date()

            logout_date = timezone.localtime(
                logout_at
            ).date()

            # Logout happened on another day.
            # Treat this session as NOT logged out.
            # Do NOT calculate any working hours.
            if logout_date != login_date:
                item["is_active"] = True
                item["logout_at"] = None
                continue

            # Invalid logout
            if logout_at <= login_at:
                continue

            interval_end = logout_at

        else:
            # -------------------------------------------------
            # NO LOGOUT = 0 WORKING HOURS
            # -------------------------------------------------
            item["is_active"] = True
            item["logout_at"] = None

            continue

        if interval_end > login_at:

            item["worked_intervals"].append(
                (
                    login_at,
                    interval_end,
                )
            )

    # ---------------------------------------------------------
    # PREPARE RESPONSE
    # ---------------------------------------------------------

    employees = []

    total_worked_seconds = 0
        
    for item in employee_data.values():

        intervals = sorted(
            item["worked_intervals"],
            key=lambda x: x[0],
        )

        merged_intervals = []

        for start, end in intervals:

            if not merged_intervals:
                merged_intervals.append(
                    [start, end]
                )
                continue

            last_start, last_end = merged_intervals[-1]

            if start <= last_end:

                if end > last_end:
                    merged_intervals[-1][1] = end

            else:
                merged_intervals.append(
                    [start, end]
                )

        item["worked_seconds"] = sum(
            int(
                (end - start).total_seconds()
            )
            for start, end in merged_intervals
        )

    for item in employee_data.values():

        worked_seconds = max(
            0,
            item["worked_seconds"],
        )

        total_worked_seconds += worked_seconds

        hours = worked_seconds // 3600

        minutes = (
            worked_seconds % 3600
        ) // 60

        employees.append({
            "employee_id": item["employee_id"],

            "employee_code": item["employee_code"],

            "name": item["name"],

            "login_at": timezone.localtime(
                item["login_at"]
            ).strftime("%H:%M:%S"),

            "logout_at": (
                timezone.localtime(
                    item["logout_at"]
                ).strftime("%H:%M:%S")
                if item["logout_at"]
                else None
            ),

            "worked_hours": (
                f"{hours}h {minutes}m"
            ),

            "worked_seconds": worked_seconds,

            "is_active": item["is_active"],
        })

    employees.sort(
        key=lambda x: x["name"].lower()
    )

    # ---------------------------------------------------------
    # TOTAL FOR THE DAY
    # ---------------------------------------------------------

    total_hours = (
        total_worked_seconds // 3600
    )

    total_minutes = (
        total_worked_seconds % 3600
    ) // 60

    return JsonResponse({
        "success": True,

        "date": selected_date.isoformat(),

        "employee_count": len(employees),

        "total_worked": (
            f"{total_hours}h "
            f"{total_minutes}m"
        ),

        "total_worked_seconds": (
            total_worked_seconds
        ),

        "employees": employees,
    })   
    
    
    
@login_required
def attendance_report(request):
    today = timezone.localdate()

    default_start = today.replace(day=1)
    default_end = today

    start_date = request.GET.get(
        "start_date",
        default_start.isoformat(),
    )

    end_date = request.GET.get(
        "end_date",
        default_end.isoformat(),
    )

    # ---------------------------------------------------------
    # VALIDATE DATES
    # ---------------------------------------------------------

    try:
        start = datetime.strptime(
            start_date,
            "%Y-%m-%d",
        ).date()

        end = datetime.strptime(
            end_date,
            "%Y-%m-%d",
        ).date()

    except (ValueError, TypeError):

        start = default_start
        end = default_end

        start_date = start.isoformat()
        end_date = end.isoformat()

    if start > end:
        start = default_start
        end = default_end

        start_date = start.isoformat()
        end_date = end.isoformat()

    # ---------------------------------------------------------
    # GET SESSIONS
    # Same source used by calendar_view/calendar_day_data
    # ---------------------------------------------------------

    sessions = (
        AttendanceSession.objects
        .filter(
            login_at__date__gte=start,
            login_at__date__lte=end,
        )
        .select_related("employee")
        .order_by(
            "login_at",
            "employee__name",
        )
    )

    now = timezone.now()

    # ---------------------------------------------------------
    # GROUP BY DATE + EMPLOYEE
    # ---------------------------------------------------------

    daily_data = defaultdict(
        lambda: {
            "employee": None,
            "date": None,
            "login_at": None,
            "logout_at": None,
            "worked_intervals": [],
            "is_active": False,
            "sessions": 0,
        }
    )

    for session in sessions:

        if session.login_at is None:
            continue

        session_date = timezone.localtime(
            session.login_at
        ).date()

        key = (
            session_date,
            session.employee.id,
        )

        item = daily_data[key]

        item["employee"] = session.employee
        item["date"] = session_date
        item["sessions"] += 1

        # -----------------------------------------------------
        # EARLIEST LOGIN
        # -----------------------------------------------------

        if (
            item["login_at"] is None
            or session.login_at < item["login_at"]
        ):
            item["login_at"] = session.login_at

        # -----------------------------------------------------
        # CHECK SESSION
        # -----------------------------------------------------

        login_at = session.login_at

        if login_at > now:
            continue

        # -----------------------------------------------------
        # NO LOGOUT = 0 HOURS
        # -----------------------------------------------------

        if not session.logout_at:
            item["is_active"] = True
            item["logout_at"] = None
            continue

        logout_at = session.logout_at

        login_date = timezone.localtime(
            login_at
        ).date()

        logout_date = timezone.localtime(
            logout_at
        ).date()

        # -----------------------------------------------------
        # CROSS-MIDNIGHT LOGOUT
        #
        # Treat as NOT LOGGED OUT.
        # Do NOT calculate working hours.
        # -----------------------------------------------------

        if logout_date != login_date:
            item["is_active"] = True
            item["logout_at"] = None
            continue

        # -----------------------------------------------------
        # INVALID LOGOUT
        # -----------------------------------------------------

        if logout_at <= login_at:
            continue

        # -----------------------------------------------------
        # LATEST VALID LOGOUT
        # -----------------------------------------------------

        if (
            item["logout_at"] is None
            or logout_at > item["logout_at"]
        ):
            item["logout_at"] = logout_at

        # -----------------------------------------------------
        # ACTUAL WORK INTERVAL
        # -----------------------------------------------------

        item["worked_intervals"].append(
            (
                login_at,
                logout_at,
            )
        )

    # ---------------------------------------------------------
    # PREPARE REPORT DATA
    # ---------------------------------------------------------

    report_data = []

    employee_totals = defaultdict(int)

    # ---------------------------------------------------------
    # MERGE OVERLAPPING INTERVALS
    # ---------------------------------------------------------

    for item in daily_data.values():

        intervals = sorted(
            item["worked_intervals"],
            key=lambda x: x[0],
        )

        merged_intervals = []

        for start_time, end_time in intervals:

            if not merged_intervals:
                merged_intervals.append(
                    [start_time, end_time]
                )
                continue

            last_start, last_end = merged_intervals[-1]

            if start_time <= last_end:

                if end_time > last_end:
                    merged_intervals[-1][1] = end_time

            else:
                merged_intervals.append(
                    [start_time, end_time]
                )

        # -----------------------------------------------------
        # CALCULATE ACTUAL WORKED SECONDS
        # -----------------------------------------------------

        worked_seconds = sum(
            int(
                (end_time - start_time).total_seconds()
            )
            for start_time, end_time in merged_intervals
        )

        # Safety
        worked_seconds = max(
            0,
            worked_seconds,
        )

        item["worked_seconds"] = worked_seconds

        employee_id = item["employee"].id

        employee_totals[employee_id] += worked_seconds

    # ---------------------------------------------------------
    # FORMAT REPORT
    # ---------------------------------------------------------

    # for item in sorted(
    #     daily_data.values(),
    #     key=lambda x: (
    #         x["date"],
    #         x["employee"].name.lower(),
    #     ),
    #     reverse=True,
    # ):

    #     worked_seconds = item.get(
    #         "worked_seconds",
    #         0,
    #     )

    #     hours = worked_seconds // 3600

    #     minutes = (
    #         worked_seconds % 3600
    #     ) // 60

    #     report_data.append({
    #         "employee": item["employee"],

    #         "date": item["date"],

    #         "login_at": (
    #             timezone.localtime(
    #                 item["login_at"]
    #             )
    #             if item["login_at"]
    #             else None
    #         ),

    #         "logout_at": (
    #             timezone.localtime(
    #                 item["logout_at"]
    #             )
    #             if item["logout_at"]
    #             else None
    #         ),

    #         "worked_seconds": worked_seconds,

    #         "worked_hours": (
    #             f"{hours}h {minutes}m"
    #         ),

    #         "sessions": item["sessions"],

    #         "is_active": item["is_active"],
    #     })

    
    # ---------------------------------------------------------
    # GROUP REPORT BY EMPLOYEE
    # ---------------------------------------------------------

    employees_data = defaultdict(list)

    for item in sorted(
        daily_data.values(),
        key=lambda x: (
            x["employee"].name.lower(),
            x["date"],
        ),
    ):

        worked_seconds = item.get(
            "worked_seconds",
            0,
        )

        worked_seconds = max(
            0,
            worked_seconds,
        )

        hours = worked_seconds // 3600

        minutes = (
            worked_seconds % 3600
        ) // 60

        employees_data[
            item["employee"].id
        ].append({

            "employee": item["employee"],

            "date": item["date"],

            "login_at": (
                timezone.localtime(
                    item["login_at"]
                )
                if item["login_at"]
                else None
            ),

            "logout_at": (
                timezone.localtime(
                    item["logout_at"]
                )
                if item["logout_at"]
                else None
            ),

            "worked_seconds": worked_seconds,

            "worked_hours": (
                f"{hours}h {minutes}m"
            ),

            "sessions": item["sessions"],

            "is_active": item["is_active"],
        })


    # ---------------------------------------------------------
    # BUILD ONE REPORT SECTION PER EMPLOYEE
    # ---------------------------------------------------------

    report_data = []

    for employee_id, records in employees_data.items():

        employee = records[0]["employee"]

        total_seconds = sum(
            record["worked_seconds"]
            for record in records
        )

        total_hours = total_seconds // 3600

        total_minutes = (
            total_seconds % 3600
        ) // 60

        report_data.append({

            "employee": employee,

            "records": records,

            "total_seconds": total_seconds,

            "employee_total": (
                f"{total_hours}h "
                f"{total_minutes}m"
            ),
        })


    # ---------------------------------------------------------
    # GRAND TOTAL
    # ---------------------------------------------------------

    grand_total_seconds = sum(
        item["total_seconds"]
        for item in report_data
    )

    grand_hours = (
        grand_total_seconds // 3600
    )

    grand_minutes = (
        grand_total_seconds % 3600
    ) // 60

    grand_total = (
        f"{grand_hours}h "
        f"{grand_minutes}m"
    )

    # ---------------------------------------------------------
    # EMPLOYEE TOTALS
    # ---------------------------------------------------------

    for item in report_data:

        total_seconds = employee_totals[
            item["employee"].id
        ]

        hours = total_seconds // 3600

        minutes = (
            total_seconds % 3600
        ) // 60

        item["employee_total"] = (
            f"{hours}h {minutes}m"
        )

    # ---------------------------------------------------------
    # GRAND TOTAL
    # ---------------------------------------------------------

    grand_total_seconds = sum(
        employee_totals.values()
    )

    grand_hours = (
        grand_total_seconds // 3600
    )

    grand_minutes = (
        grand_total_seconds % 3600
    ) // 60

    grand_total = (
        f"{grand_hours}h "
        f"{grand_minutes}m"
    )

    # ---------------------------------------------------------
    # RENDER
    # ---------------------------------------------------------

    return render(
        request,
        "attendance/report.html",
        {
            "report_data": report_data,
            "start_date": start_date,
            "end_date": end_date,
            "total_records": sum(
                len(item["records"])
                for item in report_data
            ),
            "grand_total": grand_total,
        },
    )
    
    
    
    
    
    
# @login_required
def attendance_report_pdf(request):
    today = timezone.localdate()

    default_start = today.replace(day=1)
    default_end = today

    start_date = request.GET.get(
        "start_date",
        default_start.isoformat(),
    )

    end_date = request.GET.get(
        "end_date",
        default_end.isoformat(),
    )

    # ---------------------------------------------------------
    # VALIDATE DATES
    # ---------------------------------------------------------

    try:
        start = datetime.strptime(
            start_date,
            "%Y-%m-%d",
        ).date()

        end = datetime.strptime(
            end_date,
            "%Y-%m-%d",
        ).date()

    except (ValueError, TypeError):

        start = default_start
        end = default_end

    if start > end:
        start = default_start
        end = default_end

    # ---------------------------------------------------------
    # GET SESSIONS
    # ---------------------------------------------------------

    sessions = (
        AttendanceSession.objects
        .filter(
            login_at__date__gte=start,
            login_at__date__lte=end,
        )
        .select_related("employee")
        .order_by(
            "login_at",
            "employee__name",
        )
    )

    now = timezone.now()

    # ---------------------------------------------------------
    # GROUP BY DATE + EMPLOYEE
    # ---------------------------------------------------------

    daily_data = defaultdict(
        lambda: {
            "employee": None,
            "date": None,
            "login_at": None,
            "logout_at": None,
            "worked_intervals": [],
        }
    )

    for session in sessions:

        if session.login_at is None:
            continue

        session_date = timezone.localtime(
            session.login_at
        ).date()

        key = (
            session_date,
            session.employee.id,
        )

        item = daily_data[key]

        item["employee"] = session.employee
        item["date"] = session_date

        # -----------------------------------------------------
        # EARLIEST LOGIN
        # -----------------------------------------------------

        if (
            item["login_at"] is None
            or session.login_at < item["login_at"]
        ):
            item["login_at"] = session.login_at

        login_at = session.login_at

        if login_at > now:
            continue

        # -----------------------------------------------------
        # NO LOGOUT = 0 HOURS
        # -----------------------------------------------------

        if not session.logout_at:
            item["logout_at"] = None
            continue

        logout_at = session.logout_at

        login_date = timezone.localtime(
            login_at
        ).date()

        logout_date = timezone.localtime(
            logout_at
        ).date()

        # -----------------------------------------------------
        # CROSS-MIDNIGHT
        # -----------------------------------------------------

        if logout_date != login_date:
            item["logout_at"] = None
            continue

        # -----------------------------------------------------
        # INVALID LOGOUT
        # -----------------------------------------------------

        if logout_at <= login_at:
            continue

        # -----------------------------------------------------
        # LATEST LOGOUT
        # -----------------------------------------------------

        if (
            item["logout_at"] is None
            or logout_at > item["logout_at"]
        ):
            item["logout_at"] = logout_at

        # -----------------------------------------------------
        # ACTUAL WORK INTERVAL
        # -----------------------------------------------------

        item["worked_intervals"].append(
            (
                login_at,
                logout_at,
            )
        )


    # ---------------------------------------------------------
    # PREPARE EMPLOYEE TABLES
    # ---------------------------------------------------------

    employee_reports = defaultdict(list)

    for item in daily_data.values():

        intervals = sorted(
            item["worked_intervals"],
            key=lambda x: x[0],
        )

        merged_intervals = []

        for start_time, end_time in intervals:

            if not merged_intervals:
                merged_intervals.append(
                    [start_time, end_time]
                )
                continue

            last_start, last_end = merged_intervals[-1]

            if start_time <= last_end:

                if end_time > last_end:
                    merged_intervals[-1][1] = end_time

            else:
                merged_intervals.append(
                    [start_time, end_time]
                )

        # -----------------------------------------------------
        # ACTUAL WORKED SECONDS
        # -----------------------------------------------------

        worked_seconds = sum(
            int(
                (end_time - start_time).total_seconds()
            )
            for start_time, end_time in merged_intervals
        )

        worked_seconds = max(
            0,
            worked_seconds,
        )

        item["worked_seconds"] = worked_seconds

        employee_id = item["employee"].id

        employee_reports[employee_id].append(item)


    # ---------------------------------------------------------
    # GRAND TOTAL
    # ---------------------------------------------------------

    grand_total_seconds = 0

    for records in employee_reports.values():

        grand_total_seconds += sum(
            item["worked_seconds"]
            for item in records
        )


    # ---------------------------------------------------------
    # BUILD PDF CONTENT
    # ---------------------------------------------------------
    
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        spaceAfter=8,
    )

    normal_style = ParagraphStyle(
        "ReportNormal",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
    )
    
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )

    elements = []

    elements.append(
        Paragraph(
            "Attendance Report",
            title_style,
        )
    )

    elements.append(
        Spacer(1, 6)
    )

    elements.append(
        Paragraph(
            f"Period: "
            f"{start.strftime('%d-%m-%Y')}"
            f" — "
            f"{end.strftime('%d-%m-%Y')}",
            normal_style,
        )
    )

    elements.append(
        Spacer(1, 15)
    )


    # ---------------------------------------------------------
    # ONE TABLE PER EMPLOYEE
    # ---------------------------------------------------------

    for employee_id, records in sorted(
        employee_reports.items(),
        key=lambda x: x[1][0]["employee"].name.lower(),
    ):

        employee = records[0]["employee"]

        # -----------------------------------------------------
        # EMPLOYEE NAME
        # -----------------------------------------------------

        elements.append(
            Paragraph(
                f"<b>{employee.name}</b>",
                normal_style,
            )
        )

        elements.append(
            Paragraph(
                f"Employee ID: {employee.employee_id}",
                normal_style,
            )
        )

        elements.append(
            Spacer(1, 6)
        )

        # -----------------------------------------------------
        # EMPLOYEE TABLE
        # -----------------------------------------------------

        table_data = [
            [
                "Date",
                "Login",
                "Logout",
                "Worked",
            ]
        ]

        employee_total_seconds = 0

        for item in sorted(
            records,
            key=lambda x: x["date"],
        ):

            worked_seconds = item["worked_seconds"]

            employee_total_seconds += worked_seconds

            hours = worked_seconds // 3600

            minutes = (
                worked_seconds % 3600
            ) // 60

            worked_display = (
                f"{hours}h {minutes}m"
            )

            # -------------------------------------------------
            # LOGIN
            # -------------------------------------------------

            login_display = (
                timezone.localtime(
                    item["login_at"]
                ).strftime("%H:%M")
                if item["login_at"]
                else "-"
            )

            # -------------------------------------------------
            # LOGOUT
            # -------------------------------------------------

            logout_display = (
                timezone.localtime(
                    item["logout_at"]
                ).strftime("%H:%M")
                if item["logout_at"]
                else "Working"
            )

            table_data.append([
                item["date"].strftime(
                    "%d-%m-%Y"
                ),
                login_display,
                logout_display,
                worked_display,
            ])

        # -----------------------------------------------------
        # EMPLOYEE TOTAL
        # -----------------------------------------------------

        employee_hours = (
            employee_total_seconds // 3600
        )

        employee_minutes = (
            employee_total_seconds % 3600
        ) // 60

        employee_total_display = (
            f"{employee_hours}h "
            f"{employee_minutes}m"
        )

        table_data.append([
            "",
            "",
            "Period Total",
            employee_total_display,
        ])

        # -----------------------------------------------------
        # CREATE EMPLOYEE TABLE
        # -----------------------------------------------------

        table = Table(
            table_data,
            repeatRows=1,
            colWidths=[
                45 * mm,
                35 * mm,
                35 * mm,
                40 * mm,
            ],
        )

        table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#222222"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                # Employee total row
                (
                    "FONTNAME",
                    (0, -1),
                    (-1, -1),
                    "Helvetica-Bold",
                ),
            ])
        )

        elements.append(table)

        elements.append(
            Spacer(1, 18)
        )


    # ---------------------------------------------------------
    # GRAND TOTAL
    # ---------------------------------------------------------

    grand_hours = (
        grand_total_seconds // 3600
    )

    grand_minutes = (
        grand_total_seconds % 3600
    ) // 60

    grand_total_display = (
        f"{grand_hours}h "
        f"{grand_minutes}m"
    )

    elements.append(
        Paragraph(
            f"<b>Total Worked Hours:</b> "
            f"{grand_total_display}",
            normal_style,
        )
    )
    document.build(elements)

    # ---------------------------------------------------------
    # RESPONSE
    # ---------------------------------------------------------

    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/pdf",
    )

    response[
        "Content-Disposition"
    ] = (
        'attachment; '
        'filename="attendance_report.pdf"'
    )

    return response



 
