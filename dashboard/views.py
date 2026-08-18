import datetime

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from appointments.models import Cliente, Turno, Venta
from catalog.models import Producto
from whatsapp_bot.models import MensajeWhatsApp
from tenants.models import Tenant
from .auth import propietario_o_superadmin_required, puede_administrar


def _rango_fechas(request):
    hoy = timezone.localdate()
    default_desde = hoy.replace(day=1)
    desde = request.GET.get("desde")
    hasta = request.GET.get("hasta")
    desde = datetime.date.fromisoformat(desde) if desde else default_desde
    hasta = datetime.date.fromisoformat(hasta) if hasta else hoy
    return desde, hasta


def login_salon(request, slug):
    tenant = get_object_or_404(Tenant, slug=slug)
    next_url = request.GET.get("next") or reverse("dashboard:kpis", args=[slug])

    if puede_administrar(request.user, tenant):
        return redirect(next_url)

    error = None
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if puede_administrar(user, tenant):
                login(request, user)
                return redirect(next_url)
            error = "Ese usuario no tiene acceso al panel de este salón."
        else:
            error = "Usuario o contraseña incorrectos."
    else:
        form = AuthenticationForm(request)

    return render(request, "dashboard/login.html", {"tenant": tenant, "form": form, "error": error})


def logout_salon(request, slug):
    logout(request)
    return redirect("dashboard:login", slug=slug)


@propietario_o_superadmin_required
def kpis(request, tenant):
    desde, hasta = _rango_fechas(request)

    turnos_periodo = Turno.objects.filter(
        tenant=tenant, estado=Turno.Estado.COMPLETADO,
        fecha_hora__date__gte=desde, fecha_hora__date__lte=hasta,
    )
    ventas_periodo = Venta.objects.filter(
        tenant=tenant, creado__date__gte=desde, creado__date__lte=hasta,
    )

    facturacion_turnos = turnos_periodo.aggregate(total=Sum("monto"))["total"] or 0
    facturacion_productos = ventas_periodo.aggregate(total=Sum("total"))["total"] or 0
    facturacion_total = facturacion_turnos + facturacion_productos
    cantidad_turnos = turnos_periodo.count()
    ticket_promedio = (facturacion_turnos / cantidad_turnos) if cantidad_turnos else 0

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
    facturacion_por_producto = (
        ventas_periodo.values("producto__id", "producto__nombre")
        .annotate(total=Sum("total"), cantidad=Sum("cantidad"))
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
        "facturacion_turnos": facturacion_turnos,
        "facturacion_productos": facturacion_productos,
        "cantidad_turnos": cantidad_turnos,
        "ticket_promedio": ticket_promedio,
        "facturacion_por_barbero": facturacion_por_barbero,
        "facturacion_por_servicio": facturacion_por_servicio,
        "facturacion_por_producto": facturacion_por_producto,
        "tasa_recurrencia": tasa_recurrencia,
        "ocupacion": ocupacion,
    })


@propietario_o_superadmin_required
def ranking_peluqueros(request, tenant):
    barberos = (
        tenant.barberos.filter(activo=True)
        .annotate(cantidad_resenas=Count("resenas"))
        .order_by("-rating_promedio")
    )
    umbral = tenant.umbral_alerta_rating
    return render(request, "dashboard/ranking_peluqueros.html", {
        "tenant": tenant, "barberos": barberos, "umbral": umbral,
    })


@propietario_o_superadmin_required
def turnos_list(request, tenant):
    """Todos los tratamientos/turnos del salón, para ver qué se hizo."""
    estado = request.GET.get("estado", "")
    turnos = tenant.turnos.select_related("cliente", "barbero", "servicio").all()
    if estado:
        turnos = turnos.filter(estado=estado)
    turnos = turnos[:200]
    return render(request, "dashboard/turnos.html", {
        "tenant": tenant, "turnos": turnos, "estado": estado, "estados": Turno.Estado.choices,
    })


@propietario_o_superadmin_required
def clientes_list(request, tenant):
    q = request.GET.get("q", "").strip()
    clientes = tenant.clientes.annotate(cantidad_turnos=Count("turnos")).order_by("nombre")
    if q:
        clientes = clientes.filter(nombre__icontains=q) | clientes.filter(telefono__icontains=q)
    return render(request, "dashboard/clientes.html", {"tenant": tenant, "clientes": clientes, "q": q})


@propietario_o_superadmin_required
def cliente_detalle(request, tenant, cliente_id):
    """Ficha del cliente: qué tratamientos se hizo y qué productos compró."""
    cliente = get_object_or_404(Cliente, id=cliente_id, tenant=tenant)
    turnos = cliente.turnos.select_related("barbero", "servicio").all()
    compras = cliente.compras.select_related("producto").all()
    total_gastado = (turnos.filter(estado=Turno.Estado.COMPLETADO).aggregate(t=Sum("monto"))["t"] or 0) + \
        (compras.aggregate(t=Sum("total"))["t"] or 0)
    return render(request, "dashboard/cliente_detalle.html", {
        "tenant": tenant, "cliente": cliente, "turnos": turnos, "compras": compras,
        "total_gastado": total_gastado,
    })


@propietario_o_superadmin_required
def productos_panel(request, tenant):
    """Inventario y ventas de productos."""
    productos = tenant.productos.order_by("nombre")
    ventas_recientes = tenant.ventas.select_related("producto", "cliente").all()[:30]
    clientes = tenant.clientes.order_by("nombre")
    return render(request, "dashboard/productos.html", {
        "tenant": tenant, "productos": productos, "ventas_recientes": ventas_recientes, "clientes": clientes,
    })


@propietario_o_superadmin_required
def registrar_venta(request, tenant):
    if request.method != "POST":
        return redirect("dashboard:productos", tenant.slug)

    producto = get_object_or_404(Producto, id=request.POST.get("producto"), tenant=tenant)
    cantidad = int(request.POST.get("cantidad") or 1)
    cliente_id = request.POST.get("cliente")
    cliente = Cliente.objects.filter(id=cliente_id, tenant=tenant).first() if cliente_id else None

    venta = Venta(tenant=tenant, producto=producto, cantidad=cantidad, cliente=cliente, precio_unitario=producto.precio)
    try:
        venta.save()
        messages.success(request, f"Venta registrada: {cantidad}x {producto.nombre}.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))

    return redirect("dashboard:productos", tenant.slug)


@propietario_o_superadmin_required
def mensajes_whatsapp(request, tenant):
    """Log de conversaciones de WhatsApp con clientes, para ver la atención brindada."""
    mensajes = list(tenant.mensajes_whatsapp.select_related("turno").order_by("-timestamp")[:100])
    telefonos = sorted({m.cliente_telefono for m in mensajes})
    mensajes.reverse()  # más viejo arriba, más nuevo abajo, como una conversación
    return render(request, "dashboard/whatsapp.html", {
        "tenant": tenant, "mensajes": mensajes, "telefonos": telefonos,
    })
