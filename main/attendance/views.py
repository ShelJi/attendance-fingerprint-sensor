from django.shortcuts import render
from attendance.models import AttendanceSession
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Employee
from .services import process_scan
from datetime import datetime

from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render

from django.contrib.auth.decorators import login_required

from .models import AttendanceDevice

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import EmployeeForm



@csrf_exempt
def fingerprint_test_scan(request):

    if request.method != "POST":
        return JsonResponse(
            {"error": "POST required"},
            status=405,
        )

    data = json.loads(request.body)

    fingerprint_id = data.get("fingerprint_id")
    device_id = data.get("device_id")

    return JsonResponse({
        "success": True,
        "fingerprint_id": fingerprint_id,
        "device_id": device_id,
        "message": "Fingerprint received",
    })
    
    
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
            {"error": "Invalid JSON"},
            status=400,
        )

    fingerprint_id = data.get("fingerprint_id")

    if not fingerprint_id:
        return JsonResponse(
            {"error": "fingerprint_id required"},
            status=400,
        )

    employee = Employee.objects.filter(
        fingerprint_id=fingerprint_id
    ).first()

    if employee is None:
        return JsonResponse(
            {
                "success": False,
                "error": "Employee not found",
            },
            status=404,
        )

    session, action = process_scan(
        employee=employee,
        occurred_at=timezone.now(),
    )

    return JsonResponse({
        "success": True,
        "employee": employee.name,
        "employee_id": employee.employee_id,
        "action": action,
        "session_id": session.id,
    })
 

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
        total_worked = 0

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
            "total_worked": total_worked,
        },
    )
    

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
        "last_seen": device.last_seen,
    })


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
    
    
    
    