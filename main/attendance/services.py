from django.utils import timezone
from datetime import timedelta
from attendance.models import AttendanceSession


def process_scan(employee, occurred_at):

    today = timezone.localdate()

    session = (
        AttendanceSession.objects
        .filter(
            employee=employee,
            login_at__date=today,
        )
        .order_by("-login_at")
        .first()
    )

    # First scan of the day
    if session is None:
        session = AttendanceSession.objects.create(
            employee=employee,
            login_at=occurred_at,
        )

        return session, "login"

    if occurred_at - session.login_at < timedelta(hours=1):
        return session, "You have already logged IN."

        
    session.logout_at = occurred_at
    # session.worked_hours = (
    #     session.logout_at - session.login_at
    # )
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
