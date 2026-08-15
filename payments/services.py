"""Integración con Mercado Pago Checkout Pro para cobrar la seña al reservar.

Usa el `mp_access_token` propio de cada tenant (multi-tenant desde el día
uno: cada salón cobra con su propia cuenta de Mercado Pago, la plataforma
no procesa el dinero de terceros).
"""
import logging

import mercadopago
from django.urls import reverse

from .models import Pago

logger = logging.getLogger(__name__)


class MercadoPagoNoConfigurado(Exception):
    """El tenant no tiene un access_token de Mercado Pago cargado."""


class MercadoPagoError(Exception):
    """La API de Mercado Pago devolvió un error al crear la preferencia."""


def monto_sena(turno):
    tenant = turno.tenant
    porcentaje = tenant.sena_porcentaje
    return round(turno.monto * porcentaje / 100, 2)


def _sdk(tenant):
    if not tenant.mp_access_token:
        raise MercadoPagoNoConfigurado(
            f"El salón '{tenant.nombre}' no tiene configurado el access_token de Mercado Pago."
        )
    return mercadopago.SDK(tenant.mp_access_token)


def crear_preferencia_sena(request, turno):
    """Crea una preferencia de Checkout Pro para la seña de `turno` y
    devuelve (pago, init_point) con el link de pago hosteado por Mercado Pago.
    """
    tenant = turno.tenant
    sdk = _sdk(tenant)
    monto = monto_sena(turno)

    pago = Pago.objects.create(
        turno=turno, concepto=Pago.Concepto.SENA, monto=monto, estado=Pago.Estado.PENDIENTE,
    )

    base_url = request.build_absolute_uri("/")[:-1]
    back_urls = {
        "success": base_url + reverse("payments:retorno", args=[tenant.slug, turno.id]) + "?estado=success",
        "pending": base_url + reverse("payments:retorno", args=[tenant.slug, turno.id]) + "?estado=pending",
        "failure": base_url + reverse("payments:retorno", args=[tenant.slug, turno.id]) + "?estado=failure",
    }

    preference_data = {
        "items": [{
            "title": f"Seña · {turno.servicio.nombre} con {turno.barbero.nombre}",
            "quantity": 1,
            "unit_price": float(monto),
            "currency_id": "ARS",
        }],
        "payer": {"name": turno.cliente.nombre, "phone": {"number": turno.cliente.telefono}},
        "external_reference": str(pago.id),
        "back_urls": back_urls,
        "auto_return": "approved",
        "notification_url": base_url + reverse("payments:webhook", args=[tenant.slug]),
        "statement_descriptor": tenant.nombre[:22],
    }

    try:
        response = sdk.preference().create(preference_data)
    except Exception as exc:
        pago.delete()
        raise MercadoPagoError(str(exc)) from exc

    if response.get("status") not in (200, 201):
        pago.delete()
        raise MercadoPagoError(response.get("response", response))

    body = response["response"]
    pago.mp_preference_id = body["id"]
    pago.save(update_fields=["mp_preference_id"])

    init_point = body.get("init_point") or body.get("sandbox_init_point")
    return pago, init_point


def confirmar_pago(tenant, payment_id):
    """Consulta un pago por su ID contra la API de Mercado Pago y, si está
    aprobado, confirma el turno asociado. Se usa desde el webhook y desde
    la página de retorno (por si el webhook todavía no llegó)."""
    sdk = _sdk(tenant)
    try:
        response = sdk.payment().get(payment_id)
    except Exception as exc:
        logger.warning("Error consultando pago %s en Mercado Pago: %s", payment_id, exc)
        return None

    if response.get("status") != 200:
        return None

    info = response["response"]
    pago_id = info.get("external_reference")
    if not pago_id:
        return None

    try:
        pago = Pago.objects.select_related("turno").get(id=pago_id, turno__tenant=tenant)
    except (Pago.DoesNotExist, ValueError):
        return None

    pago.mp_payment_id = str(info.get("id", payment_id))

    estado_mp = info.get("status")
    if estado_mp == "approved":
        pago.estado = Pago.Estado.APROBADO
        pago.comision_plataforma = round(pago.monto * 0.05, 2)
        pago.neto_salon = pago.monto - pago.comision_plataforma
        turno = pago.turno
        turno.sena_pagada = True
        turno.estado = turno.Estado.CONFIRMADO
        turno.pago_id_mp = pago.mp_payment_id
        turno.save(update_fields=["sena_pagada", "estado", "pago_id_mp"])
    elif estado_mp in ("rejected", "cancelled"):
        pago.estado = Pago.Estado.RECHAZADO
    pago.save()
    return pago
