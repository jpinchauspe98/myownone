from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from tenants.models import Tenant
from staff.models import Barbero
from appointments.models import Turno, Cliente


class Resena(models.Model):
    """Reseña ligada 1 a 1 al turno y, por lo tanto, al peluquero que atendió."""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="resenas")
    turno = models.OneToOneField(Turno, on_delete=models.CASCADE, related_name="resena")
    barbero = models.ForeignKey(Barbero, on_delete=models.CASCADE, related_name="resenas")
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="resenas")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.rating}★ para {self.barbero.nombre}"

    def save(self, *args, **kwargs):
        # denormalizar tenant/barbero desde el turno para evitar inconsistencias
        self.tenant = self.turno.tenant
        self.barbero = self.turno.barbero
        self.cliente = self.turno.cliente
        super().save(*args, **kwargs)
        self.barbero.recalcular_rating()
