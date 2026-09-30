from django.shortcuts import render

from attendance.models import AttendanceSession


def process_scan(employee, occurred_at):
    session = (
        AttendanceSession.objects
        .filter(employee=employee, logout_at__isnull=True)
        .order_by("-login_at")
        .first()
    )

    if session is None:
        session = AttendanceSession.objects.create(
            employee=employee,
            login_at=occurred_at,
        )
        return session, "login"

    session.logout_at = occurred_at
    session.save(update_fields=["logout_at", "updated_at"])

    return session, "logout"