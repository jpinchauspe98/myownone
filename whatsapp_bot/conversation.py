"""State machine de la conversación de reservas por WhatsApp.

saludo -> elegir servicio -> elegir peluquero -> mostrar horarios libres
-> (nombre si es cliente nuevo) -> confirmar -> (seña si el salón la pide)
"""
import datetime
import logging

from django.conf import settings

from appointments.models import Cliente, Turno
from appointments.services import formatear_fecha_hora, slots_disponibles
from catalog.models import Servicio
from payments import services as payment_services
from staff.models import Barbero
from .client import enviar_mensaje, WhatsAppNoConfigurado
from .models import ConversacionWhatsApp, MensajeWhatsApp

logger = logging.getLogger(__name__)

Paso = ConversacionWhatsApp.Paso

SALUDOS = {"hola", "buenas", "buen dia", "buenas tardes", "buenas noches", "hi", "hello", "menu", "menú"}
CANCELACIONES = {"cancelar", "salir", "chau"}
MAX_HORARIOS_MOSTRADOS = 8

_fmt = formatear_fecha_hora


def _parse_opcion(texto, cantidad):
    texto = texto.strip()
    if not texto.isdigit():
        return None
    n = int(texto)
    if 1 <= n <= cantidad:
        return n - 1
    return None


def _enviar(tenant, telefono, texto, turno=None):
    try:
        enviar_mensaje(tenant, telefono, texto, turno=turno)
    except WhatsAppNoConfigurado:
        logger.warning("Tenant %s no tiene WhatsApp Cloud API configurado, no se pudo enviar mensaje.", tenant.slug)


def procesar_mensaje_entrante(tenant, telefono, texto, perfil_nombre=None):
    """Punto de entrada desde el webhook. Loguea el mensaje entrante y
    avanza la conversación según el paso en el que esté el cliente."""
    MensajeWhatsApp.objects.create(
        tenant=tenant, cliente_telefono=telefono, direccion=MensajeWhatsApp.Direccion.IN, contenido=texto,
    )

    conv, _ = ConversacionWhatsApp.objects.get_or_create(tenant=tenant, telefono=telefono)
    texto_norm = texto.strip().lower()

    if texto_norm in CANCELACIONES and conv.paso != Paso.INICIO:
        conv.reiniciar()
        _enviar(tenant, telefono, "Reserva cancelada. Escribí 'hola' cuando quieras empezar de nuevo.")
        return

    if texto_norm in SALUDOS or conv.paso in (Paso.INICIO, Paso.FINALIZADO):
        _iniciar(tenant, conv, perfil_nombre)
        return

    handlers = {
        Paso.SERVICIO: _manejar_servicio,
        Paso.PELUQUERO: _manejar_peluquero,
        Paso.HORARIO: _manejar_horario,
        Paso.NOMBRE: _manejar_nombre,
        Paso.CONFIRMAR: _manejar_confirmar,
    }
    handler = handlers.get(conv.paso, _iniciar)
    if handler is _iniciar:
        handler(tenant, conv, perfil_nombre)
    else:
        handler(tenant, conv, texto)


def _iniciar(tenant, conv, perfil_nombre=None):
    servicios = list(tenant.servicios.filter(activo=True))
    if not servicios:
        _enviar(tenant, conv.telefono, "Por ahora no tenemos servicios cargados. Contactanos más tarde.")
        return
    lineas = [f"{i + 1}. {s.nombre} - ${s.precio}" for i, s in enumerate(servicios)]
    conv.contexto = {"servicios_ids": [s.id for s in servicios], "perfil_nombre": perfil_nombre}
    conv.paso = Paso.SERVICIO
    conv.save()
    texto = (
        f"¡Hola! 👋 Soy el asistente de reservas de *{tenant.nombre}*.\n\n"
        "¿Qué servicio querés reservar?\n" + "\n".join(lineas)
    )
    _enviar(tenant, conv.telefono, texto)


def _manejar_servicio(tenant, conv, texto):
    ids = conv.contexto.get("servicios_ids", [])
    idx = _parse_opcion(texto, len(ids))
    if idx is None:
        _enviar(tenant, conv.telefono, "No entendí 🤔 Respondé con el número del servicio que querés.")
        return

    barberos = list(tenant.barberos.filter(activo=True).order_by("-rating_promedio"))
    conv.contexto["servicio_id"] = ids[idx]
    conv.contexto["barberos_ids"] = [b.id for b in barberos]
    conv.paso = Paso.PELUQUERO
    conv.save()

    lineas = ["0. Primero disponible ⚡"]
    for i, b in enumerate(barberos):
        rating = f" (★{b.rating_promedio})" if b.rating_promedio else ""
        lineas.append(f"{i + 1}. {b.nombre}{rating}")
    _enviar(tenant, conv.telefono, "Perfecto. ¿Con qué peluquero preferís?\n" + "\n".join(lineas))


def _manejar_peluquero(tenant, conv, texto):
    barberos_ids = conv.contexto.get("barberos_ids", [])
    texto = texto.strip()
    if texto == "0":
        if not barberos_ids:
            _enviar(tenant, conv.telefono, "No tenemos peluqueros disponibles ahora mismo.")
            return
        barbero_id = barberos_ids[0]
    else:
        idx = _parse_opcion(texto, len(barberos_ids))
        if idx is None:
            _enviar(tenant, conv.telefono, "Elegí un número de la lista, o 0 para primero disponible.")
            return
        barbero_id = barberos_ids[idx]

    servicio = Servicio.objects.get(id=conv.contexto["servicio_id"])
    barbero = Barbero.objects.get(id=barbero_id)
    slots_por_dia = slots_disponibles(tenant, barbero, servicio)
    flat = [s for dia in slots_por_dia for s in dia["slots"]][:MAX_HORARIOS_MOSTRADOS]

    if not flat:
        _enviar(
            tenant, conv.telefono,
            "No hay horarios disponibles esta semana con ese peluquero. Escribí 'hola' para elegir otro.",
        )
        conv.reiniciar()
        return

    conv.contexto["barbero_id"] = barbero_id
    conv.contexto["slots"] = [s.isoformat() for s in flat]
    conv.paso = Paso.HORARIO
    conv.save()

    lineas = [f"{i + 1}. {_fmt(s)}" for i, s in enumerate(flat)]
    _enviar(tenant, conv.telefono, "Estos son los próximos horarios libres:\n" + "\n".join(lineas))


def _manejar_horario(tenant, conv, texto):
    slots = conv.contexto.get("slots", [])
    idx = _parse_opcion(texto, len(slots))
    if idx is None:
        _enviar(tenant, conv.telefono, "Elegí un número de horario de la lista.")
        return

    conv.contexto["fecha_hora"] = slots[idx]
    cliente = Cliente.objects.filter(tenant=tenant, telefono=conv.telefono).first()
    if cliente:
        conv.contexto["nombre"] = cliente.nombre
        conv.paso = Paso.CONFIRMAR
        conv.save()
        _pedir_confirmacion(tenant, conv)
    else:
        conv.paso = Paso.NOMBRE
        conv.save()
        _enviar(tenant, conv.telefono, "¿Cómo es tu nombre?")


def _manejar_nombre(tenant, conv, texto):
    nombre = texto.strip()
    if not nombre:
        _enviar(tenant, conv.telefono, "Decime tu nombre para poder reservar el turno.")
        return
    conv.contexto["nombre"] = nombre
    conv.paso = Paso.CONFIRMAR
    conv.save()
    _pedir_confirmacion(tenant, conv)


def _pedir_confirmacion(tenant, conv):
    servicio = Servicio.objects.get(id=conv.contexto["servicio_id"])
    barbero = Barbero.objects.get(id=conv.contexto["barbero_id"])
    fecha_hora = datetime.datetime.fromisoformat(conv.contexto["fecha_hora"])
    texto = (
        f"Confirmá tu turno:\n*{servicio.nombre}* con *{barbero.nombre}*\n"
        f"{_fmt(fecha_hora)}\n${servicio.precio}\n\n1. Confirmar ✅\n2. Cancelar ❌"
    )
    _enviar(tenant, conv.telefono, texto)


def _manejar_confirmar(tenant, conv, texto):
    texto = texto.strip()
    if texto not in ("1", "2"):
        _enviar(tenant, conv.telefono, "Respondé *1* para confirmar o *2* para cancelar.")
        return
    if texto == "2":
        _enviar(tenant, conv.telefono, "Reserva cancelada. Escribí 'hola' cuando quieras empezar de nuevo.")
        conv.reiniciar()
        return

    servicio = Servicio.objects.get(id=conv.contexto["servicio_id"])
    barbero = Barbero.objects.get(id=conv.contexto["barbero_id"])
    fecha_hora = datetime.datetime.fromisoformat(conv.contexto["fecha_hora"])
    nombre = conv.contexto.get("nombre") or "Cliente WhatsApp"

    cliente, creado = Cliente.objects.get_or_create(
        tenant=tenant, telefono=conv.telefono, defaults={"nombre": nombre}
    )
    if not creado and nombre and cliente.nombre != nombre:
        cliente.nombre = nombre
        cliente.save(update_fields=["nombre"])

    requiere_sena = tenant.sena_habilitada and bool(tenant.mp_access_token)
    turno = Turno.objects.create(
        tenant=tenant, cliente=cliente, barbero=barbero, servicio=servicio, fecha_hora=fecha_hora,
        estado=Turno.Estado.PENDIENTE if requiere_sena else Turno.Estado.CONFIRMADO,
        canal_origen=Turno.Canal.WHATSAPP, monto=servicio.precio,
    )

    if requiere_sena:
        try:
            _, init_point = payment_services.crear_preferencia_sena(settings.SITE_BASE_URL, turno)
        except (payment_services.MercadoPagoNoConfigurado, payment_services.MercadoPagoError):
            turno.delete()
            _enviar(tenant, conv.telefono, "No pudimos generar el link de pago. Probá de nuevo en unos minutos.")
            conv.reiniciar()
            return
        monto = payment_services.monto_sena(turno)
        _enviar(
            tenant, conv.telefono,
            f"Para confirmar tu turno pagá la seña de ${monto} acá 👇\n{init_point}\n\n"
            "Apenas se acredite el pago te confirmamos el turno.",
            turno=turno,
        )
    else:
        _enviar(
            tenant, conv.telefono,
            f"¡Listo, {cliente.nombre}! Tu turno quedó confirmado para el {_fmt(fecha_hora)}. Te esperamos 💈",
            turno=turno,
        )

    conv.reiniciar()
