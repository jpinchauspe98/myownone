from django.db import models

from appointments.models import Turno


class Pago(models.Model):
    """Registro de pago vía Mercado Pago. La integración real (Checkout Pro,
    webhooks) se construye en Fase 2 — por ahora sólo el modelo para poder
    cerrar el dashboard de facturación con datos reales cuando exista.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"
        REEMBOLSADO = "reembolsado", "Reembolsado"

    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name="pagos")
    mp_payment_id = models.CharField(max_length=100, blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    comision_plataforma = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    comision_peluquero = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    neto_salon = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"Pago {self.monto} - {self.estado}"
