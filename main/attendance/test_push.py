from datetime import timedelta
from unittest.mock import patch

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import AdminPushDevice, AttendanceSession, Employee, PushReceipt
from .push import check_receipts, send_device


class AdminPushTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("admin", password="test-password", is_staff=True)
        self.client.force_login(self.user)
        self.employee = Employee.objects.create(name="Alice", employee_id="E1", fingerprint_id="1")
        self.token = "ExponentPushToken[test-token]"

    def register(self):
        return self.client.post("/api/mobile/notifications/device/", {"token": self.token}, content_type="application/json")

    def test_registration_skips_history_and_reregistration_keeps_cursor(self):
        AttendanceSession.objects.create(employee=self.employee, login_at=timezone.now())
        self.assertEqual(self.register().status_code, 200)
        device = AdminPushDevice.objects.get()
        self.assertGreater(device.cursor, 0)
        AttendanceSession.objects.create(employee=self.employee, login_at=timezone.now())
        self.register()
        self.assertEqual(AdminPushDevice.objects.get().cursor, device.cursor)
        self.client.post("/api/mobile/auth/logout/")
        self.assertFalse(AdminPushDevice.objects.exists())

    def test_registration_requires_manager_and_valid_token(self):
        response = self.client.post("/api/mobile/notifications/device/", {"token": "bad"}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.employee.user = self.user
        self.employee.save()
        self.user.is_staff = False
        self.user.save()
        self.assertEqual(self.register().status_code, 403)
        self.client.logout()
        self.assertEqual(self.register().status_code, 401)

    def test_password_change_keeps_current_device_registered(self):
        self.register()
        response = self.client.post("/api/mobile/auth/password/", {
            "old_password": "test-password", "new_password1": "new-secure-password-827", "new_password2": "new-secure-password-827",
        }, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AdminPushDevice.objects.get().session_key, self.client.session.session_key)

    @patch("attendance.push.expo_request")
    def test_delivery_retries_failure_then_tracks_receipt(self, send):
        self.register()
        device = AdminPushDevice.objects.get()
        AttendanceSession.objects.create(employee=self.employee, login_at=timezone.now().replace(hour=13, minute=5))
        send.side_effect = requests.ConnectionError()
        with self.assertRaises(requests.ConnectionError):
            send_device(device.pk)
        self.assertEqual(AdminPushDevice.objects.get().cursor, 0)
        send.side_effect = None
        send.return_value = [{"status": "ok", "id": "ticket-1"}]
        send_device(device.pk)
        self.assertIn("checked in", send.call_args.args[1][0]["body"])
        self.assertRegex(send.call_args.args[1][0]["body"], r"\d{1,2}:\d{2} [AP]M$")
        self.assertEqual(PushReceipt.objects.get().ticket, "ticket-1")
        send.reset_mock()
        send_device(device.pk)
        send.assert_not_called()
        PushReceipt.objects.update(created_at=timezone.now() - timedelta(minutes=16))
        send.return_value = {"ticket-1": {"status": "error", "details": {"error": "DeviceNotRegistered"}}}
        check_receipts()
        self.assertFalse(AdminPushDevice.objects.exists())

    @patch("attendance.push.expo_request")
    def test_revoked_session_never_receives_push(self, send):
        self.register()
        device = AdminPushDevice.objects.get()
        self.client.session.flush()
        AttendanceSession.objects.create(employee=self.employee, login_at=timezone.now())
        send_device(device.pk)
        send.assert_not_called()
        self.assertFalse(AdminPushDevice.objects.exists())
