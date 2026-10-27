from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory

from .models import Employee, AttendanceEvidence


class EmployeeAdminTests(TestCase):
    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser("admin", password="admin-secret")
        self.client.force_login(self.superuser)

    def test_create_employee_with_automatic_credentials(self):
        response = self.client.get("/admin/attendance/employee/add/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("user", response.context["adminform"].form.fields)
        response = self.client.post("/admin/attendance/employee/add/", {
            "name": "Alice", "employee_id": "E1", "fingerprint_id": "1", "_save": "Save",
        })
        self.assertEqual(response.status_code, 302)
        employee = Employee.objects.get(employee_id="E1")
        self.assertEqual(employee.user.username, "E1")
        self.assertTrue(employee.user.check_password("12345"))
        self.assertFalse(employee.user.is_staff)
        self.assertFalse(employee.user.is_superuser)

    def test_username_collision_is_form_error(self):
        get_user_model().objects.create_user("E1", password="existing-secret")
        response = self.client.post("/admin/attendance/employee/add/", {
            "name": "Alice", "employee_id": "E1", "fingerprint_id": "1",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("employee_id", response.context["adminform"].form.errors)
        self.assertFalse(Employee.objects.exists())

    def test_password_field_can_set_and_reset_linked_account_password(self):
        data = {"name": "Alice", "employee_id": "E1", "fingerprint_id": "1", "password": "custom-strong-secret-847"}
        response = self.client.post("/admin/attendance/employee/add/", data)
        self.assertEqual(response.status_code, 302)
        employee = Employee.objects.get(employee_id="E1")
        self.assertTrue(employee.user.check_password(data["password"]))
        self.assertNotEqual(employee.user.password, data["password"])
        url = f"/admin/attendance/employee/{employee.pk}/change/"
        response = self.client.get(url)
        self.assertFalse(response.context["adminform"].form["password"].value())
        response = self.client.post(url, {**data, "user": employee.user_id, "password": ""})
        self.assertEqual(response.status_code, 302)
        employee.user.refresh_from_db()
        self.assertTrue(employee.user.check_password(data["password"]))
        response = self.client.post(url, {**data, "user": employee.user_id, "password": "12345"})
        self.assertEqual(response.status_code, 302)
        employee.user.refresh_from_db()
        self.assertTrue(employee.user.check_password("12345"))

    def test_weak_custom_password_is_rejected_without_creating_account(self):
        response = self.client.post("/admin/attendance/employee/add/", {
            "name": "Alice", "employee_id": "E1", "fingerprint_id": "1", "password": "abc",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("password", response.context["adminform"].form.errors)
        self.assertFalse(get_user_model().objects.filter(username="E1").exists())

    def test_staff_cannot_reset_superuser_password_through_employee_form(self):
        from django.contrib.auth.models import Permission

        employee = Employee.objects.create(name="Admin", employee_id="ADMIN", fingerprint_id="1", user=self.superuser)
        staff = get_user_model().objects.create_user("staff", password="staff-secret", is_staff=True)
        staff.user_permissions.add(Permission.objects.get(content_type__app_label="attendance", codename="change_employee"))
        self.client.force_login(staff)
        response = self.client.post(f"/admin/attendance/employee/{employee.pk}/change/", {
            "name": employee.name, "employee_id": employee.employee_id, "fingerprint_id": employee.fingerprint_id,
            "user": self.superuser.pk, "password": "replacement-strong-secret-938",
        })
        self.assertEqual(response.status_code, 403)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.check_password("admin-secret"))

    def test_edit_preserves_password_and_account(self):
        employee = Employee.objects.create(name="Alice", employee_id="E1", fingerprint_id="1")
        employee.user.set_password("changed-secret")
        employee.user.save()
        response = self.client.post(f"/admin/attendance/employee/{employee.pk}/change/", {
            "name": "Updated", "employee_id": "E2", "fingerprint_id": "2",
            "user": employee.user_id, "_save": "Save",
        })
        self.assertEqual(response.status_code, 302)
        employee.refresh_from_db()
        self.assertEqual((employee.name, employee.employee_id, employee.fingerprint_id), ("Updated", "E2", "2"))
        self.assertEqual(employee.user.username, "E1")
        self.assertTrue(employee.user.check_password("changed-secret"))

    def test_superuser_controls_all_attendance_models(self):
        from django.apps import apps

        request = RequestFactory().get("/admin/")
        request.user = self.superuser
        for model in apps.get_app_config("attendance").get_models():
            model_admin = admin.site._registry[model]
            self.assertTrue(model_admin.has_add_permission(request), model.__name__)
            self.assertTrue(model_admin.has_change_permission(request), model.__name__)
            self.assertTrue(model_admin.has_delete_permission(request), model.__name__)
            self.assertEqual(self.client.get(f"/admin/attendance/{model._meta.model_name}/").status_code, 200)
        evidence_admin = admin.site._registry[AttendanceEvidence]
        self.assertNotIn("work_description", evidence_admin.get_readonly_fields(request))
        request.user = get_user_model().objects.create_user("staff", is_staff=True)
        self.assertFalse(evidence_admin.has_add_permission(request))
        self.assertFalse(evidence_admin.has_delete_permission(request))
        self.assertIn("work_description", evidence_admin.get_readonly_fields(request))
