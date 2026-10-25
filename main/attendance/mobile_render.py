from django.core.paginator import Page
from django.db.models import Model, QuerySet
from django.http import JsonResponse
from django.shortcuts import render as html_render


def serialize(value):
    if isinstance(value, Model):
        data = {field.name: field.value_from_object(value) for field in value._meta.fields}
        if hasattr(value, "is_online"):
            data["is_online"] = value.is_online
        if hasattr(value, "is_active"):
            data["is_active"] = value.is_active
        return data
    if isinstance(value, Page):
        return {
            "results": serialize(list(value)),
            "page": value.number,
            "pages": value.paginator.num_pages,
            "count": value.paginator.count,
            "has_next": value.has_next(),
            "has_previous": value.has_previous(),
        }
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, QuerySet)):
        return [serialize(item) for item in value]
    return value


def render(request, template_name, context=None, *args, **kwargs):
    if not getattr(request, "mobile_api", False):
        return html_render(request, template_name, context, *args, **kwargs)
    data = serialize(context or {})
    if "calendar_days" in data:
        import json
        data["calendar_days"] = json.loads(data["calendar_days"])
    return JsonResponse(data)
