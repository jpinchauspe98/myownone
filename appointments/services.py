import datetime

from django.utils import timezone

from .models import Turno

SLOT_STEP_MIN = 30
DIAS_A_MOSTRAR = 7
DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def formatear_fecha_hora(fecha_hora):
    return f"{DIAS_ES[fecha_hora.weekday()]} {fecha_hora:%d/%m} {fecha_hora:%H:%M}"


def slots_disponibles(tenant, barbero, servicio, dias=DIAS_A_MOSTRAR):
    """Genera horarios libres para un barbero según horario del salón,
    la duración del servicio y los turnos ya ocupados. No permite horarios
    pasados. Usado tanto por la mini-web como por el bot de WhatsApp."""
    ahora = timezone.localtime()
    ocupados = set(
        tenant.turnos.filter(
            barbero=barbero,
            estado__in=[Turno.Estado.PENDIENTE, Turno.Estado.CONFIRMADO],
        ).values_list("fecha_hora", flat=True)
    )
    slots_por_dia = []
    for offset in range(dias):
        dia = (ahora + datetime.timedelta(days=offset)).date()
        inicio = datetime.datetime.combine(dia, tenant.horario_apertura, tzinfo=ahora.tzinfo)
        fin = datetime.datetime.combine(dia, tenant.horario_cierre, tzinfo=ahora.tzinfo)
        cursor = inicio
        libres = []
        while cursor + datetime.timedelta(minutes=servicio.duracion_min) <= fin:
            if cursor > ahora and cursor not in ocupados:
                libres.append(cursor)
            cursor += datetime.timedelta(minutes=SLOT_STEP_MIN)
        if libres:
            slots_por_dia.append({"dia": dia, "slots": libres})
    return slots_por_dia
