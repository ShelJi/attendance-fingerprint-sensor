import copy
import importlib
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import AttendanceEvidence, AttendanceNotification, AttendanceSession, Employee, OfficeLocation
from .services import process_scan


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class WorkplaceApiTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(name="Alice", employee_id="A1", fingerprint_id="1")
        self.other = Employee.objects.create(name="Bob", employee_id="B1", fingerprint_id="2")
        self.manager = get_user_model().objects.create_user("manager", is_staff=True)
        self.office = OfficeLocation.objects.create(name="PL Office", wifi_ssid="PL Office WiFi", wifi_bssid="aa:bb:cc:dd:ee:ff", latitude=10, longitude=76)
        self.client.force_login(self.employee.user)
        self.proof = {"action": "login", "mode": "office", "wifi_ssid": self.office.wifi_ssid, "wifi_bssid": self.office.wifi_bssid.upper(),
                      "location": {"latitude": 10, "longitude": 76, "accuracy": 10, "captured_at": timezone.now().isoformat(), "mocked": False}}

    def submit(self, payload=None):
        return self.client.post("/api/mobile/me/attendance/", payload if payload is not None else self.proof, content_type="application/json")

    def test_office_requires_both_matching_wifi_and_location(self):
        for field, value in (("wifi_ssid", "Wrong WiFi"), ("wifi_bssid", "00:00:00:00:00:00")):
            data = copy.deepcopy(self.proof); data[field] = value
            self.assertEqual(self.submit(data).status_code, 400)
        data = copy.deepcopy(self.proof); data["location"]["latitude"] = 11
        self.assertEqual(self.submit(data).status_code, 400)
        self.assertFalse(AttendanceSession.objects.exists())
        self.assertFalse(AttendanceNotification.objects.exists())
        response = self.submit()
        self.assertEqual(response.status_code, 200)
        proof = AttendanceEvidence.objects.get()
        self.assertEqual(proof.office, self.office)
        self.assertEqual(proof.wifi_bssid, self.office.wifi_bssid)
        self.assertIsNotNone(response.json()["notification_id"])

    def test_invalid_stale_mocked_or_inaccurate_locations_fail_closed(self):
        for field, value in (("latitude", 91), ("longitude", -181), ("accuracy", 0), ("accuracy", 101), ("accuracy", True), ("latitude", float("nan")),
                             ("mocked", True), ("mocked", None), ("captured_at", "2020-01-01T00:00:00Z"),
                             ("captured_at", (timezone.now() + timedelta(minutes=5)).isoformat()), ("captured_at", "2026-10-25T10:00:00")):
            with self.subTest(field=field, value=value):
                data = copy.deepcopy(self.proof); data["location"][field] = value
                self.assertEqual(self.submit(data).status_code, 400)
        self.assertFalse(AttendanceSession.objects.exists())

    def test_uncertainty_circle_and_admin_accuracy_limit_are_enforced(self):
        data = copy.deepcopy(self.proof); data["location"]["latitude"] += 0.00085
        self.assertEqual(self.submit(data).status_code, 400)
        data = copy.deepcopy(self.proof); data["location"]["accuracy"] = 60
        self.assertEqual(self.submit(data).status_code, 400)

    def test_unconfigured_office_and_legacy_unverified_posts_are_rejected(self):
        self.assertEqual(self.submit({"action": "login"}).status_code, 400)
        self.office.is_active = False; self.office.save()
        self.assertEqual(self.submit().status_code, 400)

    def test_outdoor_needs_location_place_and_description_without_any_photo(self):
        data = copy.deepcopy(self.proof)
        data.update(mode="outdoor", place_name="Client site", work_description="Installation and customer training")
        data.pop("wifi_ssid"); data.pop("wifi_bssid")
        for missing in ("place_name", "work_description", "location"):
            invalid = dict(data); invalid.pop(missing)
            self.assertEqual(self.submit(invalid).status_code, 400)
        self.assertEqual(self.submit(data).status_code, 200)
        proof = AttendanceEvidence.objects.get()
        self.assertEqual(proof.mode, "outdoor")
        self.assertEqual(proof.work_description, data["work_description"])
        self.assertFalse(any(field.name == "photo" for field in AttendanceEvidence._meta.fields))

    def test_cooldown_and_repeated_scans_do_not_duplicate_notifications(self):
        self.assertEqual(self.submit().json()["action"], "login")
        data = copy.deepcopy(self.proof); data["action"] = "logout"
        self.assertEqual(self.submit(data).json()["action"], "already_logged_in")
        self.assertEqual(AttendanceNotification.objects.count(), 1)
        self.assertEqual(AttendanceEvidence.objects.count(), 1)
        AttendanceSession.objects.update(login_at=timezone.now() - timedelta(minutes=6))
        self.assertEqual(self.submit(data).json()["action"], "logout")
        session = AttendanceSession.objects.get(); session.save()
        self.assertEqual(AttendanceNotification.objects.count(), 2)
        self.assertEqual(AttendanceEvidence.objects.count(), 2)

    def test_staff_notifications_are_self_only_and_management_sees_everyone(self):
        self.submit()
        process_scan(self.other, timezone.now())
        own = self.client.get("/api/mobile/me/notifications/?after=0").json()
        self.assertEqual([row["name"] for row in own["notifications"]], ["Alice"])
        self.assertEqual(self.client.get("/api/mobile/notifications/").status_code, 403)
        self.assertEqual(self.client.get("/api/mobile/attendance/records/").status_code, 403)
        self.assertEqual(self.client.get("/web/work-attendance/").status_code, 403)
        self.client.force_login(self.manager)
        feed = self.client.get("/api/mobile/notifications/?after=0")
        self.assertEqual(len(feed.json()["notifications"]), 2)
        self.assertIn("no-store", feed["Cache-Control"])
        cursor = feed.json()["cursor"]
        self.assertEqual(self.client.get(f"/api/mobile/notifications/?after={cursor}").json()["notifications"], [])
        self.assertEqual(self.client.get("/api/mobile/notifications/?after=-1").status_code, 400)

    def test_office_outdoor_filters_match_each_action_of_a_mixed_session(self):
        self.submit()
        AttendanceSession.objects.update(login_at=timezone.now() - timedelta(minutes=6))
        data = copy.deepcopy(self.proof); data.update(action="logout", mode="outdoor", place_name="Client office", work_description="Completed deployment")
        self.submit(data)
        self.client.force_login(self.manager)
        for mode, action in (("office", "login"), ("outdoor", "logout")):
            response = self.client.get("/api/mobile/attendance/records/", {"mode": mode})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(response.json()["records"][0]["action"], action)
        web = self.client.get("/web/work-attendance/?mode=outdoor")
        self.assertEqual(web.status_code, 200)
        self.assertContains(web, "Completed deployment")
        self.assertContains(web, "Client office")
        self.assertEqual(self.client.get("/api/mobile/attendance/records/?mode=invalid").status_code, 400)
        self.assertEqual(self.client.get("/api/mobile/attendance/records/?start_date=2026-12-31&end_date=2026-01-01").status_code, 400)

    def test_history_backfill_is_idempotent_and_preserves_device_records(self):
        session = AttendanceSession.objects.create(employee=self.employee, login_at=timezone.now() - timedelta(hours=1), logout_at=timezone.now())
        AttendanceNotification.objects.all().delete()
        migration = importlib.import_module("attendance.migrations.0006_officelocation_attendancenotification_and_more")
        migration.seed_notifications(apps, SimpleNamespace(connection=connection))
        migration.seed_notifications(apps, SimpleNamespace(connection=connection))
        self.assertEqual(AttendanceNotification.objects.filter(session=session).count(), 2)
        self.client.force_login(self.manager)
        data = self.client.get("/api/mobile/attendance/records/?mode=device").json()
        self.assertEqual(data["count"], 2)
        self.assertIsNone(data["records"][0]["verification"])

    def test_attendance_is_rolled_back_if_notification_cannot_be_written(self):
        with patch("attendance.models.AttendanceNotification.objects.get_or_create", side_effect=RuntimeError("notification write failed")):
            with self.assertRaises(RuntimeError):
                process_scan(self.employee, timezone.now())
        self.assertFalse(AttendanceSession.objects.filter(employee=self.employee).exists())
