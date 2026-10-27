from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .models import Employee, OfficeLocation
from .verification import validate_evidence


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ConfigurationTests(TestCase):
    def setUp(self):
        self.manager = get_user_model().objects.create_user("manager", is_staff=True)
        self.client.force_login(self.manager)
        self.url = "/api/mobile/configuration/offices/"
        self.data = {"name": "Office", "is_active": True, "wifi_ssid": "Office WiFi", "wifi_bssid": "AA:BB:CC:DD:EE:FF", "latitude": 10, "longitude": 76, "radius_meters": 100, "max_accuracy_meters": 50}

    def test_create_update_and_disable_configuration_used_by_staff(self):
        response = self.client.post(self.url, self.data, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        office_id = response.json()["office"]["id"]
        self.assertEqual(response.json()["office"]["wifi_bssid"], "aa:bb:cc:dd:ee:ff")
        proof = {"mode": "office", "wifi_ssid": self.data["wifi_ssid"], "wifi_bssid": self.data["wifi_bssid"], "location": {"latitude": 10, "longitude": 76, "accuracy": 5, "captured_at": timezone.now().isoformat(), "mocked": False}}
        self.assertEqual(validate_evidence(proof)["office"].pk, office_id)
        update_url = f"{self.url}{office_id}/"
        self.assertEqual(self.client.post(update_url, {**self.data, "latitude": 11, "wifi_ssid": "New WiFi"}, content_type="application/json").status_code, 200)
        with self.assertRaises(ValidationError):
            validate_evidence(proof)
        proof["wifi_ssid"] = "New WiFi"
        proof["location"]["latitude"] = 11
        self.assertEqual(validate_evidence(proof)["office"].pk, office_id)
        response = self.client.post(update_url, {**self.data, "is_active": False}, content_type="application/json")
        self.assertFalse(response.json()["office"]["is_active"])
        with self.assertRaises(ValidationError):
            validate_evidence(proof)
        self.assertEqual(len(self.client.get(self.url).json()["offices"]), 1)

    def test_invalid_configuration_does_not_save(self):
        for key, value in (("latitude", 91), ("latitude", "nan"), ("longitude", -181), ("wifi_bssid", "bad"), ("radius_meters", 9), ("max_accuracy_meters", 101), ("wifi_ssid", "")):
            with self.subTest(key=key, value=value):
                response = self.client.post(self.url, {**self.data, key: value}, content_type="application/json")
                self.assertEqual(response.status_code, 400)
                self.assertIn(key, response.json()["errors"])
        self.assertFalse(OfficeLocation.objects.exists())
        self.assertEqual(self.client.post(self.url, [], content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post(self.url + "999/", self.data, content_type="application/json").status_code, 404)

    def test_only_management_can_read_or_change_configuration(self):
        employee = Employee.objects.create(name="Alice", employee_id="E1", fingerprint_id="1")
        self.client.force_login(employee.user)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.data, content_type="application/json").status_code, 403)
        self.assertEqual(self.client.get("/web/configuration/").status_code, 403)
        self.assertEqual(self.client.post("/web/configuration/", self.data).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.assertEqual(self.client.get("/web/configuration/").status_code, 302)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.manager)
        self.assertEqual(csrf_client.post(self.url, self.data, content_type="application/json").status_code, 403)

    def test_web_form_and_dashboard_link(self):
        self.assertContains(self.client.get("/web/dashboard/"), 'App configuration')
        self.assertContains(self.client.get("/web/configuration/"), 'Use current location')
        response = self.client.post("/web/configuration/", self.data, follow=True)
        self.assertContains(response, 'Configuration saved.')
        office = OfficeLocation.objects.get()
        self.assertEqual(self.client.post(f"/web/configuration/{office.pk}/", {**self.data, "name": "Updated"}).status_code, 302)
        office.refresh_from_db()
        self.assertEqual(office.name, "Updated")
