from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.db import transaction
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator


class Employee(models.Model):
    # Legacy setting; notification delivery no longer reads this flag.
    login_notifications_enabled = models.BooleanField(default=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="employee")
    name = models.CharField(max_length=150)
    employee_id = models.CharField(max_length=50, unique=True)
    fingerprint_id = models.CharField(max_length=100, unique=True)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if not self.user_id:
                self.user = get_user_model().objects.create_user(
                    username=self.employee_id, password="12345",
                )
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_id} - {self.name}"


@receiver(post_delete, sender=Employee)
def deactivate_employee_account(sender, instance, **kwargs):
    # An orphaned employee account must never inherit legacy management access.
    get_user_model().objects.filter(pk=instance.user_id, is_staff=False, is_superuser=False).update(is_active=False)


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


class OfficeLocation(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    wifi_ssid = models.CharField(max_length=32)
    wifi_bssid = models.CharField(max_length=17, validators=[RegexValidator(
        r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", "Enter the router BSSID, e.g. AA:BB:CC:DD:EE:FF.",
    )])
    latitude = models.FloatField(validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(validators=[MinValueValidator(-180), MaxValueValidator(180)])
    radius_meters = models.PositiveIntegerField(default=100, validators=[MinValueValidator(10), MaxValueValidator(1000)])
    max_accuracy_meters = models.PositiveIntegerField(default=50, validators=[MinValueValidator(1), MaxValueValidator(100)])

    def __str__(self):
        return self.name


class AttendanceEvidence(models.Model):
    session = models.ForeignKey(AttendanceSession, on_delete=models.PROTECT, related_name="evidence")
    action = models.CharField(max_length=6, choices=[("login", "Check in"), ("logout", "Check out")])
    mode = models.CharField(max_length=7, choices=[("office", "Office"), ("outdoor", "Outdoor")])
    office = models.ForeignKey(OfficeLocation, null=True, blank=True, on_delete=models.PROTECT)
    latitude = models.FloatField()
    longitude = models.FloatField()
    accuracy_meters = models.FloatField()
    location_captured_at = models.DateTimeField()
    wifi_ssid = models.CharField(max_length=32, blank=True)
    wifi_bssid = models.CharField(max_length=17, blank=True)
    place_name = models.CharField(max_length=200, blank=True)
    work_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["session", "action"], name="one_evidence_per_attendance_action")]

    def __str__(self):
        return f"{self.session.employee} · {self.action} · {self.mode}"


class AttendanceNotification(models.Model):
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name="notifications")
    action = models.CharField(max_length=6, choices=[("login", "Check in"), ("logout", "Check out")])
    occurred_at = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["session", "action"], name="one_notification_per_attendance_action")]


class AdminPushDevice(models.Model):
    personal = models.BooleanField(default=False)
    token = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40)
    cursor = models.PositiveBigIntegerField(default=0)


class PushReceipt(models.Model):
    device = models.ForeignKey(AdminPushDevice, on_delete=models.CASCADE)
    ticket = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


@receiver(post_save, sender=AttendanceSession)
def publish_attendance_notification(sender, instance, created, **kwargs):
    if created:
        AttendanceNotification.objects.get_or_create(session=instance, action="login", defaults={"occurred_at": instance.login_at})
    if instance.logout_at is not None:
        AttendanceNotification.objects.get_or_create(session=instance, action="logout", defaults={"occurred_at": instance.logout_at})
