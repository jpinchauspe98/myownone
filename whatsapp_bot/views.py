import json
import logging

from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from tenants.models import Tenant
from . import conversation

logger = logging.getLogger(__name__)


@csrf_exempt
def webhook(request, slug):
    tenant = get_object_or_404(Tenant, slug=slug)

    if request.method == "GET":
        return _verificar(request, tenant)

    if request.method == "POST":
        _procesar_evento(request, tenant)
        return HttpResponse(status=200)

    return HttpResponse(status=405)


def _verificar(request, tenant):
    """Handshake de suscripción del webhook (Meta for Developers → WhatsApp
    → Configuration → Webhook)."""
    modo = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge", "")

    if modo == "subscribe" and token and tenant.whatsapp_verify_token and token == tenant.whatsapp_verify_token:
        return HttpResponse(challenge)
    return HttpResponseForbidden("Verify token inválido")


def _procesar_evento(request, tenant):
    try:
        body = json.loads(request.body or "{}")
    except ValueError:
        logger.warning("Webhook de WhatsApp con body no-JSON para tenant=%s", tenant.slug)
        return

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata = value.get("metadata", {})

            if tenant.whatsapp_phone_number_id and metadata.get("phone_number_id") and \
                    metadata["phone_number_id"] != tenant.whatsapp_phone_number_id:
                logger.warning(
                    "phone_number_id inesperado en webhook de tenant=%s: %s",
                    tenant.slug, metadata.get("phone_number_id"),
                )
                continue

            contactos = {c["wa_id"]: c.get("profile", {}).get("name") for c in value.get("contacts", [])}

            for mensaje in value.get("messages", []):
                if mensaje.get("type") != "text":
                    continue
                telefono = mensaje.get("from")
                texto = mensaje.get("text", {}).get("body", "")
                if not telefono or not texto:
                    continue
                try:
                    conversation.procesar_mensaje_entrante(
                        tenant, telefono, texto, perfil_nombre=contactos.get(telefono)
                    )
                except Exception:
                    logger.exception(
                        "Error procesando mensaje de WhatsApp tenant=%s telefono=%s", tenant.slug, telefono
                    )
