import json
from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.http import Http404, JsonResponse
from django.middleware.csrf import get_token
from django.urls import path
from django.views.decorators.http import require_GET, require_POST

from . import views
from .forms import EmployeeForm
from .mobile_render import serialize


def endpoint(view, methods=("GET",)):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
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
def session(request):
    return JsonResponse({
        "authenticated": request.user.is_authenticated,
        "csrf_token": get_token(request),
        "username": request.user.get_username() if request.user.is_authenticated else None,
    })


@require_POST
def sign_in(request):
    data = json_body(request)
    if data is None or not isinstance(data.get("username"), str) or not isinstance(data.get("password"), str):
        return JsonResponse({"error": "username and password strings required"}, status=400)
    user = authenticate(request, username=data["username"], password=data["password"])
    if user is None:
        return JsonResponse({"error": "Invalid credentials"}, status=401)
    login(request, user)
    return JsonResponse({"username": user.get_username(), "csrf_token": get_token(request)})


@require_POST
def sign_out(request):
    logout(request)
    return JsonResponse({"success": True})


def employee_create(request):
    data = json_body(request)
    if data is None:
        return JsonResponse({"error": "JSON object required"}, status=400)
    form = EmployeeForm(data)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    return JsonResponse({"employee": serialize(form.save())}, status=201)


urlpatterns = [
    path("auth/session/", session),
    path("auth/login/", sign_in),
    path("auth/logout/", endpoint(sign_out, ("POST",))),
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
