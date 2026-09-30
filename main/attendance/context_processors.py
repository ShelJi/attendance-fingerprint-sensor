from .models import AttendanceDevice


def device_status(request):
    device = (
        AttendanceDevice.objects
        .filter(is_active=True)
        .first()
    )

    return {
        "device": device,
    }
