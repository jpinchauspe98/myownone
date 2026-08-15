import datetime

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from appointments.models import Cliente, Turno
from catalog.models import Servicio
from payments import services
from staff.models import Barbero
from tenants.models import Tenant

SLOT_STEP_MIN = 30
DIAS_A_MOSTRAR = 7


def _get_tenant(slug):
    return get_object_or_404(Tenant, slug=slug, activo=True)


def salon_home(request, slug):
    tenant = _get_tenant(slug)
    servicios = tenant.servicios.filter(activo=True).select_related("categoria")
    barberos = tenant.barberos.filter(activo=True).prefetch_related("especialidades")
    return render(request, "webbooking/home.html", {
        "tenant": tenant, "servicios": servicios, "barberos": barberos,
    })


def _slots_disponibles(tenant, barbero, servicio, dias=DIAS_A_MOSTRAR):
    """Genera horarios libres para un barbero según horario del salón,
    la duración del servicio y los turnos ya ocupados. No permite horarios
    pasados."""
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


def reservar(request, slug):
    tenant = _get_tenant(slug)
    servicio_id = request.GET.get("servicio")
    barbero_id = request.GET.get("barbero")

    servicios = tenant.servicios.filter(activo=True)
    servicio = None
    if servicio_id:
        servicio = get_object_or_404(Servicio, id=servicio_id, tenant=tenant, activo=True)

    barberos = tenant.barberos.filter(activo=True).order_by("-rating_promedio")
    barbero = None
    primero_disponible = barbero_id == "primero_disponible"
    if barbero_id and not primero_disponible:
        barbero = get_object_or_404(Barbero, id=barbero_id, tenant=tenant, activo=True)
    elif primero_disponible and barberos:
        barbero = barberos.first()

    slots_por_dia = []
    monto_sena = None
    if servicio and barbero:
        slots_por_dia = _slots_disponibles(tenant, barbero, servicio)
        if tenant.sena_habilitada and tenant.mp_access_token:
            monto_sena = round(servicio.precio * tenant.sena_porcentaje / 100, 2)

    if request.method == "POST":
        fecha_hora_raw = request.POST.get("fecha_hora")
        nombre = request.POST.get("nombre", "").strip()
        telefono = request.POST.get("telefono", "").strip()
        if not (servicio and barbero and fecha_hora_raw and nombre and telefono):
            messages.error(request, "Completá todos los datos para confirmar el turno.")
        else:
            fecha_hora = datetime.datetime.fromisoformat(fecha_hora_raw)
            cliente, _ = Cliente.objects.get_or_create(
                tenant=tenant, telefono=telefono, defaults={"nombre": nombre}
            )
            requiere_sena = tenant.sena_habilitada and bool(tenant.mp_access_token)
            turno = Turno.objects.create(
                tenant=tenant, cliente=cliente, barbero=barbero, servicio=servicio,
                fecha_hora=fecha_hora,
                estado=Turno.Estado.PENDIENTE if requiere_sena else Turno.Estado.CONFIRMADO,
                canal_origen=Turno.Canal.WEB, monto=servicio.precio,
            )

            if requiere_sena:
                try:
                    _, init_point = services.crear_preferencia_sena(request, turno)
                except (services.MercadoPagoNoConfigurado, services.MercadoPagoError):
                    turno.delete()
                    messages.error(
                        request,
                        "No pudimos generar el link de pago de la seña. Probá de nuevo en unos minutos "
                        "o contactá al salón por WhatsApp.",
                    )
                else:
                    return redirect(init_point)
            else:
                return redirect("webbooking:confirmacion", slug=tenant.slug, turno_id=turno.id)

    return render(request, "webbooking/reservar.html", {
        "tenant": tenant, "servicios": servicios, "barberos": barberos,
        "servicio": servicio, "barbero": barbero, "primero_disponible": primero_disponible,
        "slots_por_dia": slots_por_dia, "monto_sena": monto_sena,
    })


def confirmacion(request, slug, turno_id):
    tenant = _get_tenant(slug)
    turno = get_object_or_404(Turno, id=turno_id, tenant=tenant)
    return render(request, "webbooking/confirmacion.html", {"tenant": tenant, "turno": turno})
