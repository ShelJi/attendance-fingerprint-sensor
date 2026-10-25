import math
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import OfficeLocation


def distance_meters(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta = math.radians(lon2 - lon1)
    a = math.sin((phi2 - phi1) / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta / 2) ** 2
    return 6371000 * 2 * math.asin(min(1, math.sqrt(a)))


def number(data, key, low, high):
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValidationError(f"Invalid {key}.")
    return value


def validate_evidence(data):
    mode = data.get("mode")
    if mode not in ("office", "outdoor"):
        raise ValidationError("Select office or outdoor attendance.")
    location = data.get("location")
    if not isinstance(location, dict):
        raise ValidationError("A fresh location reading is required.")
    lat = number(location, "latitude", -90, 90)
    lon = number(location, "longitude", -180, 180)
    accuracy = number(location, "accuracy", 0.1, 100)
    if location.get("mocked") is not False:
        raise ValidationError("Mocked or unverified location readings are not accepted.")
    try:
        captured = parse_datetime(location.get("captured_at", ""))
        if captured is None or timezone.is_naive(captured):
            raise ValueError
        age = timezone.now() - captured
        if not -timedelta(seconds=30) <= age <= timedelta(minutes=2):
            raise ValueError
    except (ValueError, TypeError, OverflowError):
        raise ValidationError("Location is stale or invalid. Capture your location again.")
    result = {"mode": mode, "latitude": lat, "longitude": lon, "accuracy_meters": accuracy, "location_captured_at": captured}
    if mode == "office":
        ssid, bssid = data.get("wifi_ssid"), data.get("wifi_bssid")
        if not isinstance(ssid, str) or not isinstance(bssid, str) or not ssid or not bssid:
            raise ValidationError("Connect to office Wi-Fi and allow Wi-Fi/location permissions.")
        offices = OfficeLocation.objects.filter(is_active=True, wifi_ssid=ssid, wifi_bssid__iexact=bssid)
        for office in offices:
            # Require the uncertainty circle, not just its centre, to fit in the office radius.
            if accuracy <= office.max_accuracy_meters and distance_meters(lat, lon, office.latitude, office.longitude) + accuracy <= office.radius_meters:
                result.update(office=office, wifi_ssid=ssid, wifi_bssid=bssid.lower())
                return result
        raise ValidationError("Office Wi-Fi and location must both match an active office configured by your admin.")
    for key, maximum in (("place_name", 200), ("work_description", 4000)):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
            raise ValidationError(f"{key.replace('_', ' ').capitalize()} is required (maximum {maximum} characters).")
        result[key] = value.strip()
    return result
