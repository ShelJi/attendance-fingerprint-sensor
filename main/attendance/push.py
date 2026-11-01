"""Durable notification cursor; run with the send_attendance_push command."""
import logging
import os
from datetime import timedelta

import requests
from django.contrib.sessions.models import Session
from django.db import DatabaseError, close_old_connections, transaction
from django.utils import timezone

from .decorators import is_manager
from .models import AdminPushDevice, AttendanceNotification, PushReceipt

logger = logging.getLogger(__name__)
PUSH_URL = "https://exp.host/--/api/v2/push/"


def expo_request(path, payload):
    headers = {}
    if os.environ.get("EXPO_ACCESS_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["EXPO_ACCESS_TOKEN"]
    response = requests.post(PUSH_URL + path, json=payload, headers=headers, timeout=15)
    response.raise_for_status()
    result = response.json()
    if "data" not in result:
        raise ValueError("Expo did not return push data")
    return result["data"]


def send_device(device_id):
    with transaction.atomic():
        device = AdminPushDevice.objects.select_for_update().select_related("user").filter(pk=device_id).first()
        if device is None:
            return
        session = Session.objects.filter(session_key=device.session_key, expire_date__gt=timezone.now()).first()
        allowed = hasattr(device.user, "employee") if device.personal else is_manager(device.user)
        if not device.user.is_active or not allowed or not session or str(session.get_decoded().get("_auth_user_id")) != str(device.user_id):
            device.delete()
            return
        # Also invalidate registrations after password changes/revoked sessions.
        if session.get_decoded().get("_auth_user_hash") != device.user.get_session_auth_hash():
            device.delete()
            return
        events = AttendanceNotification.objects.filter(pk__gt=device.cursor)
        if device.personal:
            events = events.filter(session__employee__user=device.user)
        events = list(events.select_related("session__employee").order_by("pk")[:100])
        if not events:
            return
        messages = []
        for event in events:
            action = "checked in" if event.action == "login" else "checked out"
            clock = timezone.localtime(event.occurred_at).strftime("%I:%M %p").lstrip("0")
            messages.append({
                "to": device.token, "title": "Attendance", "body": f"{event.session.employee.name} {action} · {clock}",
                "sound": "default", "channelId": "attendance", "priority": "high",
                "data": {"notification_id": event.pk, "occurred_at": event.occurred_at.isoformat()},
            })
        tickets = expo_request("send", messages)
        if not isinstance(tickets, list) or len(tickets) != len(events):
            raise ValueError("Expo returned an unexpected number of tickets")
        for event, ticket in zip(events, tickets):
            if ticket.get("details", {}).get("error") == "DeviceNotRegistered":
                device.delete()
                return
            if ticket.get("status") != "ok" or not ticket.get("id"):
                logger.error("Push delivery rejected for device %s: %s", device.pk, ticket.get("details", {}).get("error", "unknown error"))
                break
            PushReceipt.objects.get_or_create(ticket=ticket["id"], defaults={"device": device})
            device.cursor = event.pk
        device.save(update_fields=["cursor"])


def check_receipts():
    pending = list(PushReceipt.objects.filter(created_at__lte=timezone.now() - timedelta(minutes=15)).order_by("pk")[:1000])
    if not pending:
        return
    receipts = expo_request("getReceipts", {"ids": [item.ticket for item in pending]})
    for item in pending:
        receipt = receipts.get(item.ticket)
        if receipt is None:
            if item.created_at < timezone.now() - timedelta(hours=24):
                logger.error("Push receipt expired for device %s", item.device_id)
                item.delete()
            continue
        if receipt.get("details", {}).get("error") == "DeviceNotRegistered":
            AdminPushDevice.objects.filter(pk=item.device_id).delete()
        elif receipt.get("status") != "ok":
            logger.error("Push provider rejected device %s: %s", item.device_id, receipt.get("details", {}).get("error", "unknown error"))
        item.delete()


def dispatch_push():
    close_old_connections()
    for device_id in AdminPushDevice.objects.values_list("pk", flat=True).iterator():
        try:
            send_device(device_id)
        except (requests.RequestException, ValueError, DatabaseError):
            logger.exception("Push submission failed for device %s; will retry", device_id)
    try:
        check_receipts()
    except (requests.RequestException, ValueError):
        logger.exception("Push receipt check failed; will retry")
