import json
import logging

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt

from appointments.models import Turno
from tenants.models import Tenant
from . import services

logger = logging.getLogger(__name__)


@csrf_exempt
def webhook(request, slug):
    """Notificación asincrónica (IPN) de Mercado Pago. Debe responder rápido
    y con 200 aunque el pago no pueda procesarse, para que MP no reintente
    indefinidamente; los errores se loguean para revisión manual."""
    tenant = get_object_or_404(Tenant, slug=slug)

    payment_id = request.GET.get("data.id") or request.GET.get("id")
    topic = request.GET.get("type") or request.GET.get("topic")

    if request.method == "POST" and not payment_id:
        try:
            body = json.loads(request.body or "{}")
        except ValueError:
            body = {}
        payment_id = (body.get("data") or {}).get("id")
        topic = topic or body.get("type")

    if topic == "payment" and payment_id:
        try:
            services.confirmar_pago(tenant, payment_id)
        except Exception:
            logger.exception("Error procesando webhook de Mercado Pago para tenant=%s payment_id=%s", slug, payment_id)

    return HttpResponse(status=200)


def retorno(request, slug, turno_id):
    """Página a la que Mercado Pago redirige al cliente después de pagar
    (o cancelar) la seña. Si el webhook todavía no llegó, se consulta el
    pago directamente para no dejar al cliente esperando."""
    tenant = get_object_or_404(Tenant, slug=slug)
    turno = get_object_or_404(Turno, id=turno_id, tenant=tenant)
    estado = request.GET.get("estado")
    payment_id = request.GET.get("payment_id") or request.GET.get("collection_id")

    if payment_id and not turno.sena_pagada:
        try:
            services.confirmar_pago(tenant, payment_id)
            turno.refresh_from_db()
        except Exception:
            logger.exception("Error confirmando pago en retorno tenant=%s turno=%s", slug, turno_id)

    return render(request, "payments/retorno.html", {"tenant": tenant, "turno": turno, "estado": estado})
