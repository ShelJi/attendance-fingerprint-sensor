from django.utils import timezone
from datetime import timedelta
from attendance.models import AttendanceSession
from django.db import transaction


@transaction.atomic
def process_scan(employee, occurred_at, *, repeat_checkout=False):

    today = timezone.localdate(occurred_at)

    session = (
        AttendanceSession.objects
        .filter(
            employee=employee,
            login_at__date=today,
        )
        .order_by("-login_at")
        .first()
    )

    # First scan of the day — LOGIN
    if session is None:
        session = AttendanceSession.objects.create(
            employee=employee,
            login_at=occurred_at,
        )

        return session, "login"

    # Already logged out — allow new login session
    if session.logout_at is not None and not repeat_checkout:
        # Check cooldown
        if occurred_at - session.logout_at < timedelta(minutes=5):
            return session, "already_done"

        # Create a new session (re-login)
        session = AttendanceSession.objects.create(
            employee=employee,
            login_at=occurred_at,
        )

        return session, "login"

    # Session is active (logged in, no logout yet)
    # Check minimum work duration before allowing logout
    if occurred_at - session.login_at < timedelta(minutes=5):
        return session, "already_logged_in"

    # LOGOUT
    session.logout_at = occurred_at

    worked = session.logout_at - session.login_at
    session.worked_hours = worked - timedelta(
        microseconds=worked.microseconds
    )

    session.save(
        update_fields=[
            "logout_at",
            "worked_hours",
            "updated_at",
        ]
    )

    return session, "logout"
