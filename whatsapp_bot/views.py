import io
import json
import logging

from django.conf import settings
from django.core.management import call_command
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

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


def _cron_autorizado(request):
    """Vercel Cron manda 'Authorization: Bearer <CRON_SECRET>' solo si se
    configuró la env var CRON_SECRET en el proyecto. También se acepta
    ?secret=... para poder dispararlo a mano o desde otro scheduler."""
    if not settings.CRON_SECRET:
        return False
    auth = request.headers.get("Authorization", "")
    token = auth[len("Bearer "):].strip() if auth.startswith("Bearer ") else request.GET.get("secret", "")
    return token == settings.CRON_SECRET


@require_GET
def cron_enviar_recordatorios(request):
    if not _cron_autorizado(request):
        return HttpResponseForbidden("no autorizado")
    out = io.StringIO()
    call_command("enviar_recordatorios", stdout=out)
    return HttpResponse(out.getvalue(), content_type="text/plain")


@require_GET
def cron_solicitar_resenas(request):
    if not _cron_autorizado(request):
        return HttpResponseForbidden("no autorizado")
    out = io.StringIO()
    call_command("solicitar_resenas", stdout=out)
    return HttpResponse(out.getvalue(), content_type="text/plain")


@require_GET
def migrar(request):
    """Dispara `migrate` contra la base configurada. Pensado para correrlo
    a mano una vez después de cada deploy con cambios de modelos, en un
    hosting serverless donde no hay una consola para correr manage.py
    directamente. migrate es idempotente, así que no pasa nada si se
    llama de más."""
    if not _cron_autorizado(request):
        return HttpResponseForbidden("no autorizado")
    out = io.StringIO()
    call_command("migrate", stdout=out)
    return HttpResponse(out.getvalue(), content_type="text/plain")


@require_GET
def setup_inicial(request):
    """Crea el superusuario inicial (o le resetea la contraseña si ya
    existe) y siembra el tenant demo LEOLEIVA. Pensado para correrse una
    sola vez después del primer deploy en un hosting sin consola. La
    contraseña viene por query param (?password=...) para no dejarla
    hardcodeada en el código."""
    if not _cron_autorizado(request):
        return HttpResponseForbidden("no autorizado")

    password = request.GET.get("password")
    if not password:
        return HttpResponse("falta ?password=... en la URL", status=400, content_type="text/plain")

    from django.contrib.auth import get_user_model
    User = get_user_model()
    user, creado = User.objects.get_or_create(username="admin", defaults={"is_staff": True, "is_superuser": True})
    user.is_staff = True
    user.is_superuser = True
    user.set_password(password)
    user.save()

    out = io.StringIO()
    call_command("seed_leoleiva", stdout=out)

    return HttpResponse(
        f"superusuario 'admin' {'creado' if creado else 'actualizado'}\n\n{out.getvalue()}",
        content_type="text/plain",
    )
