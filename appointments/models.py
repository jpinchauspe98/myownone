from django.db import models

from tenants.models import Tenant
from staff.models import Barbero
from catalog.models import Servicio, Producto


class Cliente(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="clientes")
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    class Meta:
        unique_together = ("tenant", "telefono")

    def __str__(self):
        return f"{self.nombre} ({self.telefono})"


class Turno(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        CONFIRMADO = "confirmado", "Confirmado"
        COMPLETADO = "completado", "Completado"
        CANCELADO = "cancelado", "Cancelado"
        NO_SHOW = "no_show", "No se presentó"

    class Canal(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        WEB = "web", "Mini-web"
        ADMIN = "admin", "Cargado manualmente"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="turnos")
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="turnos")
    barbero = models.ForeignKey(Barbero, on_delete=models.PROTECT, related_name="turnos")
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name="turnos")
    fecha_hora = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    canal_origen = models.CharField(max_length=20, choices=Canal.choices, default=Canal.WEB)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    sena_pagada = models.BooleanField(default=False)
    pago_id_mp = models.CharField(max_length=100, blank=True)
    resena_solicitada = models.BooleanField(default=False)
    completado_en = models.DateTimeField(
        null=True, blank=True,
        help_text="Se completa solo cuando el turno pasa a estado 'completado', para disparar la solicitud de reseña 2hs después",
    )
    recordatorio_24h_enviado = models.BooleanField(default=False)
    recordatorio_2h_enviado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_hora"]

    def __str__(self):
        return f"{self.cliente.nombre} con {self.barbero.nombre} - {self.fecha_hora:%d/%m %H:%M}"

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        # Sólo se valida al crear un turno nuevo que todavía no ocurrió
        # (pendiente/confirmado). Un turno completado/cancelado/no-show
        # representa algo que ya pasó, así que no aplica la regla.
        es_turno_futuro = self.estado in (self.Estado.PENDIENTE, self.Estado.CONFIRMADO)
        if self.pk is None and es_turno_futuro and self.fecha_hora and self.fecha_hora < timezone.now():
            raise ValidationError("No se pueden crear turnos en fechas pasadas.")

    def save(self, *args, **kwargs):
        from django.utils import timezone
        self.clean()
        if self.estado == self.Estado.COMPLETADO and self.completado_en is None:
            self.completado_en = timezone.now()
        super().save(*args, **kwargs)


class Venta(models.Model):
    """Venta de un producto del salón (mostrador, no ligada a un turno).
    Descuenta stock automáticamente al crearse."""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="ventas")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="ventas")
    cliente = models.ForeignKey(
        Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name="compras"
    )
    barbero = models.ForeignKey(
        Barbero, on_delete=models.SET_NULL, null=True, blank=True, related_name="ventas_realizadas",
        help_text="Quién atendió la venta, para poder repartir comisión si corresponde",
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.pk is None and self.producto_id and self.cantidad > self.producto.stock:
            raise ValidationError(
                f"Stock insuficiente: quedan {self.producto.stock} unidades de {self.producto.nombre}."
            )

    def save(self, *args, **kwargs):
        self.clean()
        es_nueva = self.pk is None
        if not self.precio_unitario:
            self.precio_unitario = self.producto.precio
        self.total = self.precio_unitario * self.cantidad
        super().save(*args, **kwargs)
        if es_nueva:
            Producto.objects.filter(pk=self.producto_id).update(
                stock=models.F("stock") - self.cantidad
            )
