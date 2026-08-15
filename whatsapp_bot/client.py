"""Cliente delgado sobre Meta WhatsApp Cloud API (Graph API). No usa un SDK
porque la API de envío de mensajes de texto es un único POST — un SDK
completo sería sobreingeniería para lo que este bot necesita.
"""
import logging

import requests

from .models import MensajeWhatsApp

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v21.0"


class WhatsAppNoConfigurado(Exception):
    """El tenant no tiene cargado phone_number_id o access_token."""


def enviar_mensaje(tenant, telefono, texto, turno=None):
    """Envía un mensaje de texto por WhatsApp Cloud API y lo deja logueado
    en MensajeWhatsApp (tanto si se envió con éxito como si falló, para
    poder auditar conversaciones rotas)."""
    MensajeWhatsApp.objects.create(
        tenant=tenant, cliente_telefono=telefono, direccion=MensajeWhatsApp.Direccion.OUT,
        contenido=texto, turno=turno,
    )

    if not (tenant.whatsapp_phone_number_id and tenant.whatsapp_access_token):
        raise WhatsAppNoConfigurado(
            f"El salón '{tenant.nombre}' no tiene configurado WhatsApp Cloud API."
        )

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{tenant.whatsapp_phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {tenant.whatsapp_access_token}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto},
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
    except requests.RequestException:
        # Errores de red/timeout no deben tumbar al llamador (el webhook o
        # los comandos de cron que procesan varios turnos en batch): se
        # loguean para revisión manual, igual que un error HTTP de Meta.
        logger.exception("Error de red enviando WhatsApp a %s (tenant=%s)", telefono, tenant.slug)
        return None

    if response.status_code >= 400:
        logger.warning(
            "Error enviando WhatsApp a %s (tenant=%s): %s %s",
            telefono, tenant.slug, response.status_code, response.text,
        )
    return response
