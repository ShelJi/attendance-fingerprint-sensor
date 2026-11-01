import json
import re
from functools import wraps

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.http import Http404, JsonResponse
from django.core.exceptions import ValidationError
from django.middleware.csrf import get_token
from django.urls import path
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.cache import never_cache

from . import views
from .forms import EmployeeForm, OfficeLocationForm
from .mobile_render import serialize
from .models import AdminPushDevice, AttendanceNotification, Employee, AttendanceEvidence, OfficeLocation
from .services import process_scan
from .decorators import is_manager
from .verification import validate_evidence
from .activity import attendance_records, notifications, my_notifications


def endpoint(view, methods=("GET",), management=True):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        if management and not is_manager(request.user):
            return JsonResponse({"error": "Management access required"}, status=403)
        if request.method not in methods:
            response = JsonResponse({"error": "Method not allowed"}, status=405)
            response["Allow"] = ", ".join(methods)
            return response
        request.mobile_api = True
        try:
            return view(request, *args, **kwargs)
        except Http404:
            return JsonResponse({"error": "Not found"}, status=404)
    return wrapped


def json_body(request):
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


@require_GET
@never_cache
def session(request):
    return JsonResponse({
        "authenticated": request.user.is_authenticated,
        "csrf_token": get_token(request),
        "username": request.user.get_username() if request.user.is_authenticated else None,
        **native_session(request),
    })


def native_session(request):
    if request.headers.get("X-App-Client") != "native":
        return {}
    return {"session_key": request.session.session_key if request.user.is_authenticated else None}


@require_POST
@never_cache
def sign_in(request):
    data = json_body(request)
    if data is None or not isinstance(data.get("username"), str) or not isinstance(data.get("password"), str):
        return JsonResponse({"error": "username and password strings required"}, status=400)
    user = authenticate(request, username=data["username"], password=data["password"])
    if user is None:
        return JsonResponse({"error": "Invalid credentials"}, status=401)
    login(request, user)
    return JsonResponse({"username": user.get_username(), "csrf_token": get_token(request), **native_session(request)})


@require_POST
@never_cache
def sign_out(request):
    AdminPushDevice.objects.filter(user=request.user, session_key=request.session.session_key).delete()
    logout(request)
    return JsonResponse({"success": True, **native_session(request)})


def push_device(request):
    data = json_body(request)
    token = data.get("token") if data else None
    if not isinstance(token, str) or not re.fullmatch(r"(?:Exponent|Expo)PushToken\[[A-Za-z0-9_-]{1,200}\]", token):
        return JsonResponse({"error": "Valid Expo push token required"}, status=400)
    with transaction.atomic():
        device, created = AdminPushDevice.objects.get_or_create(token=token, defaults={
            "user": request.user, "session_key": request.session.session_key,
            "cursor": AttendanceNotification.objects.order_by("-pk").values_list("pk", flat=True).first() or 0,
        })
        if not created and (device.user_id != request.user.pk or device.session_key != request.session.session_key):
            device.user = request.user
            device.session_key = request.session.session_key
            device.cursor = AttendanceNotification.objects.order_by("-pk").values_list("pk", flat=True).first() or 0
            device.save()
            device.pushreceipt_set.all().delete()
    return JsonResponse({"success": True})


@never_cache
def change_password(request):
    data = json_body(request)
    fields = ("old_password", "new_password1", "new_password2")
    if data is None or any(not isinstance(data.get(key), str) for key in fields):
        return JsonResponse({"error": "old_password, new_password1 and new_password2 strings required"}, status=400)
    form = PasswordChangeForm(request.user, data)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    old_session_key = request.session.session_key
    user = form.save()
    update_session_auth_hash(request, user)
    AdminPushDevice.objects.filter(user=user, session_key=old_session_key).update(session_key=request.session.session_key)
    return JsonResponse({"success": True, "csrf_token": get_token(request), **native_session(request)})


def my_attendance(request):
    employee = Employee.objects.filter(user=request.user).first()
    if employee is None:
        return JsonResponse({"error": "No employee profile linked to this account"}, status=403)
    action = None
    notification_id = None
    if request.method == "POST":
        data = json_body(request)
        if data is None or data.get("action") not in ("login", "logout"):
            return JsonResponse({"error": "action must be login or logout"}, status=400)
        try:
            proof = validate_evidence(data)
        except ValidationError as error:
            return JsonResponse({"error": " ".join(error.messages)}, status=400)
        # Serialize mobile submissions; process_scan retains the sensor's cooldown rules.
        with transaction.atomic():
            Employee.objects.filter(pk=employee.pk).update(name=F("name"))
            latest = employee.attendance_sessions.filter(login_at__date=timezone.localdate()).order_by("-login_at").first()
            expected = "logout" if latest and latest.logout_at is None else "login"
            if data["action"] != expected:
                return JsonResponse({"error": "Attendance changed. Refresh and try again."}, status=409)
            attendance_session, action = process_scan(employee, timezone.now())
            if action in ("login", "logout"):
                AttendanceEvidence.objects.create(session=attendance_session, action=action, **proof)
                notification_id = attendance_session.notifications.get(action=action).pk
    sessions = employee.attendance_sessions.filter(login_at__date=timezone.localdate()).order_by("-login_at")
    latest = sessions.first()
    return JsonResponse({
        "employee": serialize(employee), "username": request.user.get_username(),
        "checked_in": bool(latest and latest.logout_at is None),
        "sessions": serialize(sessions), "action": action,
        "notification_id": notification_id,
        "verification": {"office_configured": OfficeLocation.objects.filter(is_active=True).exists()},
        "evidence": [{
            "id": item.pk, "session_id": item.session_id, "action": item.action, "mode": item.mode,
            "place_name": item.place_name, "work_description": item.work_description,
            "latitude": item.latitude, "longitude": item.longitude, "accuracy_meters": item.accuracy_meters,
        } for item in AttendanceEvidence.objects.filter(session__in=sessions).order_by("created_at")],
    })


def employee_create(request):
    data = json_body(request)
    if data is None:
        return JsonResponse({"error": "JSON object required"}, status=400)
    form = EmployeeForm(data)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    return JsonResponse({"employee": serialize(form.save())}, status=201)


def office_configuration(request, office_id=None):
    office = get_object_or_404(OfficeLocation, pk=office_id) if office_id else None
    if request.method == "POST":
        data = json_body(request)
        if data is None:
            return JsonResponse({"error": "JSON object required"}, status=400)
        form = OfficeLocationForm(data, instance=office)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
        return JsonResponse({"office": serialize(form.save())}, status=200 if office else 201)
    if office:
        return JsonResponse({"office": serialize(office)})
    return JsonResponse({"offices": serialize(OfficeLocation.objects.order_by("name", "pk"))})


urlpatterns = [
    path("notifications/device/", endpoint(push_device, ("POST",))),
    path("configuration/offices/", endpoint(office_configuration, ("GET", "POST"))),
    path("configuration/offices/<int:office_id>/", endpoint(office_configuration, ("GET", "POST"))),
    path("auth/session/", session),
    path("auth/login/", sign_in),
    path("auth/logout/", endpoint(sign_out, ("POST",), management=False)),
    path("auth/password/", endpoint(change_password, ("POST",), management=False)),
    path("me/attendance/", endpoint(my_attendance, ("GET", "POST"), management=False)),
    path("me/notifications/", endpoint(my_notifications, management=False)),
    path("attendance/records/", endpoint(attendance_records)),
    path("notifications/", endpoint(notifications)),
    path("employees/", endpoint(views.employee_list)),
    path("employees/create/", endpoint(employee_create, ("POST",))),
    path("employees/<int:employee_id>/", endpoint(views.employee_detail)),
    path("dashboard/", endpoint(views.dashboard)),
    path("device/control/", endpoint(views.device_control)),
    path("device/control/command/", endpoint(views.device_control_command, ("POST",))),
    path("device/control/result/", endpoint(views.device_control_result)),
    path("calendar/", endpoint(views.calendar_view)),
    path("calendar/day/", endpoint(views.calendar_day_data)),
    path("report/", endpoint(views.attendance_report)),
    path("report/pdf/", endpoint(views.attendance_report_pdf)),
]
