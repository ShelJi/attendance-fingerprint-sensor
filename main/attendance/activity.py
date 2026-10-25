from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from .decorators import management_required
from .models import AttendanceEvidence, AttendanceNotification


def events_query():
    proof = AttendanceEvidence.objects.filter(session_id=OuterRef("session_id"), action=OuterRef("action"))
    return AttendanceNotification.objects.select_related("session__employee").prefetch_related("session__evidence__office").annotate(
        work_mode=Coalesce(Subquery(proof.values("mode")[:1]), Value("device")),
    )


def event_data(event, detailed=False):
    employee = event.session.employee
    data = {"id": event.pk, "employee_id": employee.pk, "employee_code": employee.employee_id,
            "name": employee.name, "session_id": event.session_id, "action": event.action,
            "occurred_at": event.occurred_at.isoformat(), "mode": event.work_mode}
    if detailed:
        proof = next((item for item in event.session.evidence.all() if item.action == event.action), None)
        data["verification"] = None if proof is None else {
            "office": str(proof.office) if proof.office else None,
            "latitude": proof.latitude, "longitude": proof.longitude, "accuracy_meters": proof.accuracy_meters,
            "captured_at": proof.location_captured_at.isoformat(), "wifi_ssid": proof.wifi_ssid,
            "wifi_bssid": proof.wifi_bssid, "place_name": proof.place_name, "work_description": proof.work_description,
        }
    return data


def records_data(request):
    today = timezone.localdate()
    first = today.replace(day=1)
    last = (first + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    try:
        start = date.fromisoformat(request.GET.get("start_date") or first.isoformat())
        end = date.fromisoformat(request.GET.get("end_date") or last.isoformat())
        if start > end:
            raise ValueError
    except (ValueError, TypeError):
        raise ValidationError("Enter valid start/end dates in YYYY-MM-DD order.")
    mode = request.GET.get("mode", "")
    if mode not in ("", "office", "outdoor", "device"):
        raise ValidationError("Select all, office, outdoor, or device attendance.")
    events = events_query().filter(occurred_at__date__gte=start, occurred_at__date__lte=end)
    totals = {"office": 0, "outdoor": 0, "device": 0}
    totals.update({item["work_mode"]: item["total"] for item in events.values("work_mode").annotate(total=Count("id"))})
    if mode:
        events = events.filter(work_mode=mode)
    page = Paginator(events.order_by("-occurred_at", "-id"), 50).get_page(request.GET.get("page"))
    return {"records": [event_data(item, detailed=True) for item in page], "totals": totals, "mode": mode,
            "start_date": start.isoformat(), "end_date": end.isoformat(), "page": page.number,
            "pages": page.paginator.num_pages, "count": page.paginator.count,
            "has_next": page.has_next(), "has_previous": page.has_previous()}


def attendance_records(request):
    try:
        response = JsonResponse(records_data(request))
    except ValidationError as error:
        response = JsonResponse({"error": " ".join(error.messages)}, status=400)
    response["Cache-Control"] = "private, no-store"
    return response


def notifications(request, personal=False):
    query = events_query()
    if personal:
        query = query.filter(session__employee__user=request.user)
    after = request.GET.get("after")
    if after is None:
        events = list(reversed(list(query.order_by("-id")[:20])))
        cursor = events[-1].pk if events else 0
        more = False
    else:
        try:
            cursor = int(after)
            if cursor < 0:
                raise ValueError
        except (ValueError, TypeError):
            return JsonResponse({"error": "after must be a non-negative notification ID"}, status=400)
        events = list(query.filter(pk__gt=cursor).order_by("id")[:100])
        cursor = events[-1].pk if events else cursor
        more = query.filter(pk__gt=cursor).exists()
    response = JsonResponse({"notifications": [event_data(item) for item in events], "cursor": cursor, "has_more": more})
    response["Cache-Control"] = "private, no-store"
    return response


def my_notifications(request):
    return notifications(request, personal=True)


@management_required
def work_attendance(request):
    try:
        data = records_data(request)
    except ValidationError as error:
        return render(request, "attendance/work_attendance.html", {"error": " ".join(error.messages)}, status=400)
    return render(request, "attendance/work_attendance.html", data)
