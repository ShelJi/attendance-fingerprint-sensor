from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .decorators import management_required
from .forms import OfficeLocationForm
from .models import OfficeLocation


@management_required
@require_http_methods(["GET", "POST"])
def app_configuration(request, office_id=None):
    office = get_object_or_404(OfficeLocation, pk=office_id) if office_id else None
    form = OfficeLocationForm(request.POST if request.method == "POST" else None, instance=office)
    if request.method == "POST" and form.is_valid():
        office = form.save()
        return redirect(f"/web/configuration/{office.pk}/?saved=1")
    return render(request, "attendance/configuration.html", {
        "form": form, "office": office, "offices": OfficeLocation.objects.order_by("name", "pk"),
        "saved": request.GET.get("saved") == "1",
    })
