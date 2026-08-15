"""API de 'tools' para que un bot conversacional externo con LLM (ej. Forja,
corriendo en Cloudflare Workers) opere el sistema de turnos por HTTP en vez
de que la conversación viva hardcodeada en Django. Reutiliza exactamente
la misma lógica de negocio que la mini-web y el bot de reglas
(appointments/services.slots_disponibles, payments/services), para no
tener tres implementaciones distintas de "cómo se reserva un turno".
"""
import datetime
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from appointments.models import Cliente, Turno
from appointments.services import slots_disponibles
from payments import services as payment_services
from .authentication import con_tenant_autenticado


@require_GET
@con_tenant_autenticado
def servicios(request, tenant):
    data = [
        {
            "id": s.id,
            "nombre": s.nombre,
            "precio": float(s.precio),
            "duracion_min": s.duracion_min,
            "categoria": s.categoria.nombre if s.categoria else None,
        }
        for s in tenant.servicios.filter(activo=True)
    ]
    return JsonResponse({"servicios": data})


@require_GET
@con_tenant_autenticado
def peluqueros(request, tenant):
    data = [
        {
            "id": b.id,
            "nombre": b.nombre,
            "rating_promedio": float(b.rating_promedio),
            "especialidades": [e.nombre for e in b.especialidades.all()],
        }
        for b in tenant.barberos.filter(activo=True).order_by("-rating_promedio")
    ]
    return JsonResponse({"peluqueros": data})


def _resolver_barbero(tenant, peluquero_id):
    """peluquero_id puede ser el id de un Barbero, o "primero_disponible"
    (o vacío) para que se elija el de mejor rating, igual que en la
    mini-web y el bot de reglas."""
    if peluquero_id and peluquero_id != "primero_disponible":
        return tenant.barberos.filter(id=peluquero_id, activo=True).first()
    return tenant.barberos.filter(activo=True).order_by("-rating_promedio").first()


@require_GET
@con_tenant_autenticado
def horarios_disponibles(request, tenant):
    servicio_id = request.GET.get("servicio_id")
    peluquero_id = request.GET.get("peluquero_id", "")
    if not servicio_id:
        return JsonResponse({"error": "falta_servicio_id"}, status=400)

    servicio = tenant.servicios.filter(id=servicio_id, activo=True).first()
    if servicio is None:
        return JsonResponse({"error": "servicio_no_encontrado"}, status=404)

    barbero = _resolver_barbero(tenant, peluquero_id)
    if barbero is None:
        return JsonResponse({"error": "peluquero_no_encontrado"}, status=404)

    slots_por_dia = slots_disponibles(tenant, barbero, servicio)
    dias = [
        {
            "fecha": d["dia"].isoformat(),
            "horarios": [{"fecha_hora": s.isoformat(), "hora": s.strftime("%H:%M")} for s in d["slots"]],
        }
        for d in slots_por_dia
    ]
    return JsonResponse({"peluquero_id": barbero.id, "peluquero_nombre": barbero.nombre, "dias": dias})


@csrf_exempt
@require_POST
@con_tenant_autenticado
def crear_turno(request, tenant):
    try:
        body = json.loads(request.body or "{}")
    except ValueError:
        return JsonResponse({"error": "body_invalido"}, status=400)

    servicio_id = body.get("servicio_id")
    peluquero_id = body.get("peluquero_id", "")
    fecha_hora_raw = body.get("fecha_hora")
    cliente_nombre = (body.get("cliente_nombre") or "").strip()
    cliente_telefono = (body.get("cliente_telefono") or "").strip()

    if not all([servicio_id, fecha_hora_raw, cliente_nombre, cliente_telefono]):
        return JsonResponse({
            "error": "faltan_campos",
            "requeridos": ["servicio_id", "fecha_hora", "cliente_nombre", "cliente_telefono"],
        }, status=400)

    servicio = tenant.servicios.filter(id=servicio_id, activo=True).first()
    if servicio is None:
        return JsonResponse({"error": "servicio_no_encontrado"}, status=404)

    barbero = _resolver_barbero(tenant, peluquero_id)
    if barbero is None:
        return JsonResponse({"error": "peluquero_no_encontrado"}, status=404)

    try:
        fecha_hora = datetime.datetime.fromisoformat(fecha_hora_raw)
    except (TypeError, ValueError):
        return JsonResponse({"error": "fecha_hora_invalida"}, status=400)

    cliente, cliente_creado = Cliente.objects.get_or_create(
        tenant=tenant, telefono=cliente_telefono, defaults={"nombre": cliente_nombre}
    )
    if not cliente_creado and cliente_nombre and cliente.nombre != cliente_nombre:
        cliente.nombre = cliente_nombre
        cliente.save(update_fields=["nombre"])

    requiere_sena = tenant.sena_habilitada and bool(tenant.mp_access_token)
    try:
        turno = Turno.objects.create(
            tenant=tenant, cliente=cliente, barbero=barbero, servicio=servicio, fecha_hora=fecha_hora,
            estado=Turno.Estado.PENDIENTE if requiere_sena else Turno.Estado.CONFIRMADO,
            canal_origen=Turno.Canal.WHATSAPP, monto=servicio.precio,
        )
    except ValidationError as exc:
        return JsonResponse({"error": "turno_invalido", "detalle": exc.messages}, status=400)

    if not requiere_sena:
        return JsonResponse({
            "turno_id": turno.id, "estado": turno.estado, "requiere_pago": False,
            "servicio": servicio.nombre, "peluquero": barbero.nombre, "fecha_hora": turno.fecha_hora.isoformat(),
        }, status=201)

    try:
        _, init_point = payment_services.crear_preferencia_sena(settings.SITE_BASE_URL, turno)
    except (payment_services.MercadoPagoNoConfigurado, payment_services.MercadoPagoError) as exc:
        turno.delete()
        return JsonResponse({"error": "error_generando_link_pago", "detalle": str(exc)}, status=502)

    return JsonResponse({
        "turno_id": turno.id, "estado": turno.estado, "requiere_pago": True,
        "monto_sena": float(payment_services.monto_sena(turno)), "link_pago": init_point,
        "servicio": servicio.nombre, "peluquero": barbero.nombre, "fecha_hora": turno.fecha_hora.isoformat(),
    }, status=201)


@require_GET
@con_tenant_autenticado
def turno_detalle(request, tenant, turno_id):
    turno = tenant.turnos.filter(id=turno_id).select_related("barbero", "servicio").first()
    if turno is None:
        return JsonResponse({"error": "turno_no_encontrado"}, status=404)
    return JsonResponse({
        "id": turno.id, "estado": turno.estado, "sena_pagada": turno.sena_pagada,
        "servicio": turno.servicio.nombre, "peluquero": turno.barbero.nombre,
        "fecha_hora": turno.fecha_hora.isoformat(), "monto": float(turno.monto),
    })


@csrf_exempt
@require_POST
@con_tenant_autenticado
def cancelar_turno(request, tenant, turno_id):
    turno = tenant.turnos.filter(id=turno_id).first()
    if turno is None:
        return JsonResponse({"error": "turno_no_encontrado"}, status=404)
    if turno.estado in (Turno.Estado.COMPLETADO, Turno.Estado.CANCELADO):
        return JsonResponse({"error": "no_se_puede_cancelar", "estado_actual": turno.estado}, status=409)
    turno.estado = Turno.Estado.CANCELADO
    turno.save(update_fields=["estado"])
    return JsonResponse({"turno_id": turno.id, "estado": turno.estado})
