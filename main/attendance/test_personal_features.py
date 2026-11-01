from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import AdminPushDevice, AttendanceEvidence, AttendanceSession, Employee
from .push import send_device


class PersonalFeaturesTests(TestCase):
    def setUp(self):
        self.alice = Employee.objects.create(name="Alice Private", employee_id="A1", fingerprint_id="1")
        self.bob = Employee.objects.create(name="Bob Secret", employee_id="B1", fingerprint_id="2")
        self.now = timezone.now()
        for employee in (self.alice, self.bob):
            AttendanceSession.objects.create(employee=employee, login_at=self.now - timedelta(hours=2), logout_at=self.now - timedelta(hours=1), worked_hours=timedelta(hours=1))
        AttendanceEvidence.objects.create(session=self.bob.attendance_sessions.first(), action="login", mode="outdoor", latitude=10, longitude=76, accuracy_meters=10, location_captured_at=self.now, place_name="Secret location", work_description="Secret client work")
        self.client.force_login(self.alice.user)

    def test_personal_read_endpoints_ignore_other_employee_ids(self):
        day = timezone.localdate().isoformat()
        for path in ("profile/", f"calendar/?year={timezone.localdate().year}&month={timezone.localdate().month}", f"calendar/day/?date={day}", "report/", "attendance/records/", "notifications/"):
            separator = "&" if "?" in path else "?"
            response = self.client.get("/api/mobile/me/" + path + separator + f"employee_id={self.bob.pk}&user_id={self.bob.user_id}")
            self.assertEqual(response.status_code, 200, path)
            self.assertNotIn(self.bob.name, response.content.decode(), path)
            self.assertNotIn(self.bob.employee_id, response.content.decode(), path)
            self.assertNotIn("Secret client work", response.content.decode(), path)
        self.assertEqual(self.client.get("/api/mobile/me/profile/").json()["employee"]["id"], self.alice.pk)
        data = self.client.get("/api/mobile/me/report/").json()
        self.assertEqual(len(data["report_data"]), 1)
        self.assertEqual(data["report_data"][0]["employee"]["id"], self.alice.pk)
        self.assertEqual(self.client.get("/api/mobile/me/attendance/records/").json()["count"], 2)
        self.assertEqual(self.client.get("/api/mobile/me/attendance/records/").json()["totals"]["outdoor"], 0)
        calendar = self.client.get(f"/api/mobile/me/calendar/?year={timezone.localdate().year}&month={timezone.localdate().month}").json()
        self.assertEqual(calendar["calendar_days"][0]["employee_count"], 1)

    def test_personal_pdf_contains_only_own_rows(self):
        with patch("attendance.views.SimpleDocTemplate.build") as build:
            response = self.client.get(f"/api/mobile/me/report/pdf/?employee_id={self.bob.pk}")
        self.assertEqual(response.status_code, 200)
        story = repr(build.call_args.args[0])
        self.assertIn(self.alice.name, story)
        self.assertNotIn(self.bob.name, story)
        self.assertTrue(self.client.get("/api/mobile/me/report/pdf/").content.startswith(b"%PDF"))

    def test_calendar_and_report_source_filters_use_checkin_evidence_and_keep_privacy(self):
        device = self.alice.attendance_sessions.first()
        AttendanceEvidence.objects.create(session=device, action="logout", mode="outdoor", latitude=10, longitude=76, accuracy_meters=10, location_captured_at=self.now, place_name="Office", work_description="Work")
        app = AttendanceSession.objects.create(employee=self.alice, login_at=self.now - timedelta(hours=4), logout_at=self.now - timedelta(hours=3))
        AttendanceEvidence.objects.create(session=app, action="login", mode="office", latitude=10.1234567, longitude=76.7654321, accuracy_meters=10, location_captured_at=self.now)
        day = timezone.localdate(app.login_at)
        for source, expected in (("app", app), ("device", device)):
            detail = self.client.get(f"/api/mobile/me/calendar/day/?date={day}&source={source}&employee_id={self.bob.pk}").json()
            self.assertEqual(detail["employee_count"], 1)
            person = detail["employees"][0]
            self.assertEqual(person["employee_id"], self.alice.pk)
            self.assertEqual([item["id"] for item in person["sessions"]], [expected.pk])
            calendar = self.client.get(f"/api/mobile/me/calendar/?year={day.year}&month={day.month}&source={source}").json()
            self.assertEqual(calendar["calendar_days"][0][source + "_logins"], 1)
            report = self.client.get(f"/api/mobile/me/report/?start_date={day}&end_date={day}&source={source}").json()
            row = report["report_data"][0]["records"][0]
            self.assertEqual(row[source + "_logins"], 1)
            self.assertEqual(row["sessions"], 1)
            self.assertNotIn(self.bob.name, str(report))
            with patch("attendance.views.SimpleDocTemplate.build") as build:
                response = self.client.get(f"/api/mobile/me/report/pdf/?start_date={day}&end_date={day}&source={source}")
            self.assertEqual(response.status_code, 200)
            story = repr(build.call_args.args[0])
            self.assertIn("App logins" if source == "app" else "Device logins", story)
            self.assertNotIn(self.bob.name, story)
        mixed = self.client.get(f"/api/mobile/me/report/?start_date={day}&end_date={day}").json()["report_data"][0]["records"][0]
        self.assertEqual((mixed["app_logins"], mixed["device_logins"], mixed["sessions"]), (1, 1, 2))

    def test_session_locations_are_action_specific_and_private(self):
        session = self.alice.attendance_sessions.first()
        for action, latitude, longitude in (("login", 10.1234567, 76.7654321), ("logout", 10.2234567, 76.8654321)):
            AttendanceEvidence.objects.create(session=session, action=action, mode="outdoor", latitude=latitude, longitude=longitude, accuracy_meters=10, location_captured_at=self.now, place_name="Office", work_description="Work")
        data = self.client.get("/api/mobile/me/profile/").json()
        evidence = data["page_obj"]["results"][0]["evidence"]
        self.assertEqual(len(evidence), 2)
        self.assertEqual({item["action"]: item["latitude"] for item in evidence}, {"login": 10.1234567, "logout": 10.2234567})
        self.assertNotIn("Secret location", str(data))

    @patch("attendance.push.expo_request")
    def test_checkin_notifications_stay_enabled_even_with_old_preference_disabled(self, send):
        self.alice.login_notifications_enabled = False
        self.alice.save(update_fields=["login_notifications_enabled"])
        url = "/api/mobile/me/notification-settings/"
        self.assertTrue(self.client.get(url).json()["enabled"])
        self.assertTrue(self.client.post(url, {"enabled": False}, content_type="application/json").json()["enabled"])
        self.client.post("/api/mobile/me/notifications/device/", {"token": "ExponentPushToken[preferences-test]"}, content_type="application/json")
        device = AdminPushDevice.objects.get()
        AttendanceSession.objects.create(employee=self.alice, login_at=self.now, logout_at=self.now + timedelta(hours=1))
        send.return_value = [{"status": "ok", "id": "login-ticket"}, {"status": "ok", "id": "checkout-ticket"}]
        send_device(device.pk)
        messages = send.call_args.args[1]
        self.assertEqual(len(messages), 2)
        self.assertIn("checked in", messages[0]["body"])
        self.assertIn("checked out", messages[1]["body"])

    @patch("attendance.push.expo_request")
    def test_test_notification_targets_current_device_and_does_not_create_attendance(self, send):
        from .models import AttendanceNotification, PushReceipt
        token = "ExponentPushToken[test-button]"
        self.client.post("/api/mobile/me/notifications/device/", {"token": token}, content_type="application/json")
        url = "/api/mobile/me/notifications/test/"
        before = AttendanceNotification.objects.count()
        self.assertEqual(self.client.post(url, {"token": "another-device", "test_id": "sample"}, content_type="application/json").status_code, 403)
        send.assert_not_called()
        send.return_value = [{"status": "ok", "id": "test-ticket"}]
        response = self.client.post(url, {"token": token, "test_id": "sample"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["sent"])
        self.assertEqual(send.call_args.args[1][0]["to"], token)
        self.assertEqual(send.call_args.args[1][0]["data"], {"test_id": "sample"})
        self.assertEqual(AttendanceNotification.objects.count(), before)
        self.assertTrue(PushReceipt.objects.filter(ticket="test-ticket").exists())
        send.return_value = [{"status": "error", "details": {"error": "DeviceNotRegistered"}}]
        self.assertEqual(self.client.post(url, {"token": token, "test_id": "retry"}, content_type="application/json").status_code, 502)
        self.assertFalse(AdminPushDevice.objects.filter(token=token).exists())

    def test_staff_cannot_use_management_or_legacy_pdf_endpoints(self):
        for path in ("employees/", f"employees/{self.bob.pk}/", "dashboard/", "calendar/", "report/", "report/pdf/", "attendance/records/", "notifications/", "device/control/", "configuration/offices/"):
            self.assertEqual(self.client.get("/api/mobile/" + path).status_code, 403, path)
        self.assertEqual(self.client.get("/web/report/pdf/").status_code, 403)
        self.assertEqual(self.client.get(f"/api/mobile/me/profile/{self.bob.pk}/").status_code, 404)

    def test_personal_routes_require_a_linked_authenticated_account(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/mobile/me/profile/").status_code, 401)
        user = get_user_model().objects.create_user("unlinked", password="test-password")
        self.client.force_login(user)
        for path in ("profile/", "calendar/", "report/", "report/pdf/", "attendance/records/"):
            self.assertEqual(self.client.get("/api/mobile/me/" + path).status_code, 403)

    @patch("attendance.push.expo_request")
    def test_personal_push_delivers_only_own_events(self, send):
        response = self.client.post("/api/mobile/me/notifications/device/", {"token": "ExponentPushToken[staff-test]"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        device = AdminPushDevice.objects.get()
        self.assertTrue(device.personal)
        AttendanceSession.objects.create(employee=self.bob, login_at=self.now)
        AttendanceSession.objects.create(employee=self.alice, login_at=self.now)
        send.return_value = [{"status": "ok", "id": "personal-ticket"}]
        send_device(device.pk)
        messages = send.call_args.args[1]
        self.assertEqual(len(messages), 1)
        self.assertIn(self.alice.name, messages[0]["body"])
        self.assertNotIn(self.bob.name, messages[0]["body"])
