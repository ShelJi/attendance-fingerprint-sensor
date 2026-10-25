from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from .models import AttendanceSession, Employee, OfficeLocation


class StaffApiTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(name="Alice", employee_id="E1", fingerprint_id="1")
        self.other = Employee.objects.create(name="Bob", employee_id="E2", fingerprint_id="2")
        self.client.force_login(self.employee.user)
        OfficeLocation.objects.create(name="Office", wifi_ssid="PL", wifi_bssid="aa:bb:cc:dd:ee:ff", latitude=10, longitude=76)
        self.proof = {"mode": "office", "wifi_ssid": "PL", "wifi_bssid": "aa:bb:cc:dd:ee:ff", "location": {"latitude": 10, "longitude": 76, "accuracy": 10, "captured_at": timezone.now().isoformat(), "mocked": False}}

    def test_default_credentials_and_no_password_reset_on_edit(self):
        client = Client()
        self.assertEqual(client.post("/api/mobile/auth/login/", {"username": "E1", "password": "E1"}, content_type="application/json").status_code, 200)
        self.employee.user.set_password("changed-secret")
        self.employee.user.save()
        self.employee.name = "Updated"
        self.employee.save()
        self.employee.user.refresh_from_db()
        self.assertTrue(self.employee.user.check_password("changed-secret"))

    def test_management_access_is_denied(self):
        for route in ("employees/", "dashboard/", "device/control/", "report/", "employees/create/"):
            self.assertEqual(self.client.get("/api/mobile/" + route).status_code, 403)
        self.assertEqual(self.client.get("/web/employees/").status_code, 403)

    def test_deleted_employee_account_is_deactivated(self):
        user = self.employee.user
        Employee.objects.filter(pk=self.employee.pk).delete()
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertEqual(self.client.get("/api/mobile/dashboard/").status_code, 401)

    def test_attendance_is_self_only_and_cooldown_is_preserved(self):
        url = "/api/mobile/me/attendance/"
        response = self.client.post(url, {**self.proof, "action": "login", "employee_id": self.other.pk}, content_type="application/json")
        self.assertEqual(response.json()["action"], "login")
        self.assertFalse(AttendanceSession.objects.filter(employee=self.other).exists())
        self.assertEqual(self.client.post(url, {**self.proof, "action": "login"}, content_type="application/json").status_code, 409)
        response = self.client.post(url, {**self.proof, "action": "logout"}, content_type="application/json")
        self.assertEqual(response.json()["action"], "already_logged_in")
        AttendanceSession.objects.filter(employee=self.employee).update(login_at=timezone.now() - timedelta(minutes=6))
        response = self.client.post(url, {**self.proof, "action": "logout"}, content_type="application/json")
        self.assertEqual(response.json()["action"], "logout")
        self.assertFalse(response.json()["checked_in"])
        self.assertEqual(self.client.post(url, {}, content_type="application/json").status_code, 400)

    def test_password_validation_and_session_survives(self):
        url = "/api/mobile/auth/password/"
        data = {"old_password": "wrong", "new_password1": "new-strong-secret-847", "new_password2": "new-strong-secret-847"}
        self.assertEqual(self.client.post(url, data, content_type="application/json").status_code, 400)
        data["old_password"] = "E1"
        response = self.client.post(url, data, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.client.get("/api/mobile/auth/session/").json()["authenticated"])
        self.employee.user.refresh_from_db()
        self.assertTrue(self.employee.user.check_password(data["new_password1"]))
        self.assertFalse(self.employee.user.check_password("E1"))

    def test_csrf_and_anonymous_protection(self):
        client = Client(enforce_csrf_checks=True)
        for route in ("auth/password/", "me/attendance/"):
            self.assertEqual(client.get("/api/mobile/" + route).status_code, 401)
        client.force_login(self.employee.user)
        self.assertEqual(client.post("/api/mobile/me/attendance/", {"action": "login"}, content_type="application/json").status_code, 403)

    def test_unlinked_management_account_cannot_record_attendance(self):
        self.client.force_login(get_user_model().objects.create_user("manager", password="secret"))
        self.assertEqual(self.client.get("/api/mobile/me/attendance/").status_code, 403)
