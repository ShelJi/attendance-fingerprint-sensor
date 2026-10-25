from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def is_manager(user):
    # Preserve access for existing management accounts without employee profiles.
    return user.is_staff or user.is_superuser or not hasattr(user, "employee")


def management_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not is_manager(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped
