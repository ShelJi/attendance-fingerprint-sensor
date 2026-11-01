from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from .models import AttendanceSession, Employee


class FingerprintCheckoutTests(TestCase):
    def test_repeated_checkout_updates_same_session_and_message(self):
        employee = Employee.objects.create(name="Alice", employee_id="E1", fingerprint_id="1")
        start = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
        scans = [start, start + timedelta(hours=1), start + timedelta(hours=1, minutes=1), start + timedelta(hours=2)]
        for index, scanned_at in enumerate(scans):
            with patch("attendance.views.timezone.now", return_value=scanned_at):
                response = self.client.post(reverse("fingerprint_scan"), {"fingerprint_id": "1"}, content_type="application/json")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["action"], "login" if index == 0 else "logout")
            if index:
                self.assertIn("CHECKED OUT", response.json()["message"])
                session = AttendanceSession.objects.get(employee=employee)
                self.assertEqual(session.logout_at, scanned_at)
                self.assertEqual(session.worked_hours, scanned_at - start)

        with patch("attendance.views.timezone.now", return_value=start + timedelta(days=1)):
            response = self.client.post(reverse("fingerprint_scan"), {"fingerprint_id": "1"}, content_type="application/json")
        self.assertEqual(response.json()["action"], "login")
        self.assertEqual(AttendanceSession.objects.filter(employee=employee).count(), 2)
