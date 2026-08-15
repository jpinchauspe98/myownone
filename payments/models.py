from django.db import models

from appointments.models import Turno


class Pago(models.Model):
    """Registro de pago vía Mercado Pago (seña al reservar y/o pago total
    al finalizar el servicio)."""

    class Concepto(models.TextChoices):
        SENA = "sena", "Seña"
        TOTAL = "total", "Pago total"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"
        REEMBOLSADO = "reembolsado", "Reembolsado"

    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name="pagos")
    concepto = models.CharField(max_length=10, choices=Concepto.choices, default=Concepto.SENA)
    mp_preference_id = models.CharField(max_length=100, blank=True)
    mp_payment_id = models.CharField(max_length=100, blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    comision_plataforma = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    comision_peluquero = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    neto_salon = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"Pago {self.get_concepto_display()} {self.monto} - {self.estado}"
