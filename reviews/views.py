from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from appointments.models import Turno
from tenants.models import Tenant
from .models import Resena


def dejar_resena(request, slug, turno_id):
    tenant = get_object_or_404(Tenant, slug=slug, activo=True)
    turno = get_object_or_404(Turno, id=turno_id, tenant=tenant)

    if turno.estado != Turno.Estado.COMPLETADO:
        return render(request, "reviews/no_disponible.html", {"tenant": tenant, "turno": turno})

    if hasattr(turno, "resena"):
        return render(request, "reviews/gracias.html", {"tenant": tenant, "resena": turno.resena})

    if request.method == "POST":
        rating = request.POST.get("rating")
        comentario = request.POST.get("comentario", "")
        if rating not in ("1", "2", "3", "4", "5"):
            messages.error(request, "Elegí un puntaje de 1 a 5.")
        else:
            resena = Resena.objects.create(
                turno=turno, tenant=tenant, barbero=turno.barbero, cliente=turno.cliente,
                rating=int(rating), comentario=comentario,
            )
            return render(request, "reviews/gracias.html", {"tenant": tenant, "resena": resena})

    return render(request, "reviews/form.html", {"tenant": tenant, "turno": turno})
