from django.db import models


class Employee(models.Model):
    name = models.CharField(max_length=150)
    employee_id = models.CharField(max_length=50, unique=True)
    fingerprint_id = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.employee_id} - {self.name}"


class AttendanceSession(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="attendance_sessions",
    )
    login_at = models.DateTimeField()
    logout_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_active(self):
        return self.logout_at is None

    def __str__(self):
        status = "Active" if self.is_active else "Completed"
        return f"{self.employee.employee_id} - {self.login_at} - {status}"
