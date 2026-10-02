from datetime import timedelta
from django.utils import timezone
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
    
    worked_hours = models.DurationField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_active(self):
        return self.logout_at is None

    def __str__(self):
        status = "Active" if self.is_active else "Completed"
        return f"{self.employee.employee_id} - {self.login_at} - {status}"


class AttendanceDevice(models.Model):
    device_id = models.CharField(
        max_length=100,
        unique=True,
    )

    last_seen = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.device_id

    @property
    def is_online(self):
        if self.last_seen is None:
            return False

        return timezone.now() - self.last_seen < timedelta(minutes=2)
    
    
class DeviceCommand(models.Model):
    COMMAND_CHOICES = [
        ("LIST_IDS", "List IDs"),
        ("ENROLL", "Enroll"),
        ("ENROLL_AUTO", "Automatic Enroll"),
        ("DELETE", "Delete"),
        ("REPLACE", "Replace"),
        ("VERIFY", "Verify"),
        ("SUMMARY", "Database Summary"),
        ("INFO", "Sensor Information"),
    ]

    device = models.ForeignKey(
        AttendanceDevice,
        on_delete=models.CASCADE,
        related_name="commands",
    )

    command = models.CharField(
        max_length=30,
        choices=COMMAND_CHOICES,
    )

    fingerprint_id = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        default="pending",
    )

    result = models.JSONField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    
    