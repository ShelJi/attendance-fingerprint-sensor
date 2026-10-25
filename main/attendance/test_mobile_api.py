from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from .models import AttendanceSession, Employee


class MobileApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("mobile", password="test-password")
        self.employee = Employee.objects.create(name="Alice", employee_id="E1", fingerprint_id="1")
        self.client.force_login(self.user)

    def test_existing_web_routes_still_render_html(self):
        for prefix in ("/api/", "/web/"):
            response = self.client.get(prefix + "employees/")
            self.assertEqual(response.status_code, 200)
            self.assertIn("text/html", response["Content-Type"])

    def test_mobile_payloads_match_existing_view_context(self):
        now = timezone.now()
        AttendanceSession.objects.create(
            employee=self.employee, login_at=now - timedelta(hours=2),
            logout_at=now - timedelta(hours=1), worked_hours=timedelta(hours=1),
        )
        for route, key in (("employees/", "employee_data"), ("dashboard/", "total_employees"),
                           ("calendar/", "year"), ("report/", "grand_total")):
            web = self.client.get("/web/" + route)
            mobile = self.client.get("/api/mobile/" + route)
            self.assertEqual(mobile.status_code, 200)
            if key == "employee_data":
                self.assertEqual(mobile.json()[key][0]["employee"]["id"], self.employee.id)
                self.assertEqual(mobile.json()[key][0]["last_action"], web.context[key][0]["last_action"])
            else:
                self.assertEqual(mobile.json()[key], web.context[key])
        self.assertIsInstance(self.client.get("/api/mobile/calendar/").json()["calendar_days"], list)
        detail = self.client.get(f"/api/mobile/employees/{self.employee.id}/").json()
        self.assertEqual(detail["page_obj"]["count"], 1)
        self.assertEqual(detail["total_worked"], "1h 0m")

    def test_create_reuses_form_validation(self):
        url = "/api/mobile/employees/create/"
        response = self.client.post(url, {"name": "Bob", "employee_id": "E2", "fingerprint_id": "2"}, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        duplicate = self.client.post(url, {"name": "Bob", "employee_id": "E2", "fingerprint_id": "2"}, content_type="application/json")
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("employee_id", duplicate.json()["errors"])
        self.assertEqual(self.client.post(url, "[]", content_type="application/json").status_code, 400)

    def test_authentication_methods_and_not_found(self):
        self.assertEqual(self.client.post("/api/mobile/dashboard/").status_code, 405)
        self.assertEqual(self.client.get("/api/mobile/employees/999/").status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get("/api/mobile/dashboard/").status_code, 401)

    def test_session_login_csrf_and_logout(self):
        client = Client(enforce_csrf_checks=True)
        token = client.get("/api/mobile/auth/session/").json()["csrf_token"]
        url = "/api/mobile/auth/login/"
        credentials = {"username": "mobile", "password": "test-password"}
        self.assertEqual(client.post(url, credentials, content_type="application/json").status_code, 403)
        response = client.post(url, credentials, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.get("/api/mobile/dashboard/").status_code, 200)
        response = client.post("/api/mobile/auth/logout/", HTTP_X_CSRFTOKEN=response.json()["csrf_token"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.get("/api/mobile/dashboard/").status_code, 401)
