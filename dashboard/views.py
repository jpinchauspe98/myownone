import datetime

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count, Sum
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from appointments.models import Turno
from reviews.models import Resena
from staff.models import Barbero
from tenants.models import Tenant


def _rango_fechas(request):
    hoy = timezone.localdate()
    default_desde = hoy.replace(day=1)
    desde = request.GET.get("desde")
    hasta = request.GET.get("hasta")
    desde = datetime.date.fromisoformat(desde) if desde else default_desde
    hasta = datetime.date.fromisoformat(hasta) if hasta else hoy
    return desde, hasta


@staff_member_required
def kpis(request, slug):
    tenant = get_object_or_404(Tenant, slug=slug)
    desde, hasta = _rango_fechas(request)

    turnos_periodo = Turno.objects.filter(
        tenant=tenant, estado=Turno.Estado.COMPLETADO,
        fecha_hora__date__gte=desde, fecha_hora__date__lte=hasta,
    )

    facturacion_total = turnos_periodo.aggregate(total=Sum("monto"))["total"] or 0
    cantidad_turnos = turnos_periodo.count()
    ticket_promedio = (facturacion_total / cantidad_turnos) if cantidad_turnos else 0

    facturacion_por_barbero = (
        turnos_periodo.values("barbero__id", "barbero__nombre")
        .annotate(total=Sum("monto"), cantidad=Count("id"))
        .order_by("-total")
    )
    facturacion_por_servicio = (
        turnos_periodo.values("servicio__id", "servicio__nombre")
        .annotate(total=Sum("monto"), cantidad=Count("id"))
        .order_by("-total")
    )

    clientes_del_periodo = turnos_periodo.values("cliente_id").distinct().count()
    clientes_recurrentes = (
        turnos_periodo.values("cliente_id")
        .annotate(cantidad=Count("id"))
        .filter(cantidad__gt=1)
        .count()
    )
    tasa_recurrencia = (clientes_recurrentes / clientes_del_periodo * 100) if clientes_del_periodo else 0

    total_slots_estimados = tenant.barberos.filter(activo=True).count() * (hasta - desde).days * 16
    ocupacion = (cantidad_turnos / total_slots_estimados * 100) if total_slots_estimados else 0

    return render(request, "dashboard/kpis.html", {
        "tenant": tenant, "desde": desde, "hasta": hasta,
        "facturacion_total": facturacion_total,
        "cantidad_turnos": cantidad_turnos,
        "ticket_promedio": ticket_promedio,
        "facturacion_por_barbero": facturacion_por_barbero,
        "facturacion_por_servicio": facturacion_por_servicio,
        "tasa_recurrencia": tasa_recurrencia,
        "ocupacion": ocupacion,
    })


@staff_member_required
def ranking_peluqueros(request, slug):
    tenant = get_object_or_404(Tenant, slug=slug)
    barberos = (
        tenant.barberos.filter(activo=True)
        .annotate(cantidad_resenas=Count("resenas"))
        .order_by("-rating_promedio")
    )
    umbral = tenant.umbral_alerta_rating
    return render(request, "dashboard/ranking_peluqueros.html", {
        "tenant": tenant, "barberos": barberos, "umbral": umbral,
    })
