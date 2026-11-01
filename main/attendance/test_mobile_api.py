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
        employee = Employee.objects.get(employee_id="E2")
        self.assertTrue(employee.user.check_password("12345"))
        self.assertNotIn("password", response.json()["employee"])
        duplicate = self.client.post(url, {"name": "Bob", "employee_id": "E2", "fingerprint_id": "2"}, content_type="application/json")
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("employee_id", duplicate.json()["errors"])
        self.assertEqual(self.client.post(url, "[]", content_type="application/json").status_code, 400)

    def test_create_with_custom_password_can_login_and_change_it(self):
        password = "custom-strong-secret-847"
        response = self.client.post("/api/mobile/employees/create/", {
            "name": "Bob", "employee_id": "E2", "fingerprint_id": "2", "password": password,
        }, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.json()["employee"])
        staff = Client()
        self.assertEqual(staff.post("/api/mobile/auth/login/", {"username": "E2", "password": password}, content_type="application/json").status_code, 200)
        response = staff.post("/api/mobile/auth/password/", {
            "old_password": password, "new_password1": "replacement-strong-secret-938", "new_password2": "replacement-strong-secret-938",
        }, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(staff.get("/api/mobile/auth/session/").json()["authenticated"])
        employee = Employee.objects.get(employee_id="E2")
        self.assertFalse(employee.user.check_password(password))
        self.assertTrue(employee.user.check_password("replacement-strong-secret-938"))

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

    def test_native_session_restores_without_cookie_jar_and_retains_csrf_checks(self):
        def request(path, data=None, key=None, csrf=None):
            client = Client(enforce_csrf_checks=True)
            cookie = "; ".join(value for value in (
                f"sessionid={key}" if key else "", f"csrftoken={csrf}" if csrf else "",
            ) if value)
            headers = {"HTTP_X_APP_CLIENT": "native", "HTTP_COOKIE": cookie}
            if data is None:
                return client.get("/api/mobile/" + path, **headers)
            if csrf:
                headers["HTTP_X_CSRFTOKEN"] = csrf
            return client.post("/api/mobile/" + path, data, content_type="application/json", **headers)

        credentials = {"username": "mobile", "password": "test-password"}
        self.assertEqual(request("auth/login/", credentials).status_code, 403)
        initial = request("auth/session/").json()
        self.assertIsNone(initial["session_key"])
        response = request("auth/login/", credentials, csrf=initial["csrf_token"])
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        key = response.json()["session_key"]
        restored = request("auth/session/", key=key).json()
        self.assertTrue(restored["authenticated"])
        self.assertEqual(restored["username"], "mobile")
        self.assertNotIn("session_key", self.client.get("/api/mobile/auth/session/").json())
        self.assertEqual(request("auth/password/", {}, key=key).status_code, 403)
        changed = request("auth/password/", {
            "old_password": "test-password", "new_password1": "new-secure-password-837", "new_password2": "new-secure-password-837",
        }, key=key, csrf=restored["csrf_token"])
        self.assertEqual(changed.status_code, 200)
        new_key = changed.json()["session_key"]
        self.assertNotEqual(new_key, key)
        self.assertFalse(request("auth/session/", key=key).json()["authenticated"])
        self.assertTrue(request("auth/session/", key=new_key).json()["authenticated"])
        self.assertEqual(request("auth/logout/", {}, key=new_key, csrf=changed.json()["csrf_token"]).status_code, 200)
        self.assertFalse(request("auth/session/", key=new_key).json()["authenticated"])
