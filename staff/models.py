from django.conf import settings
from django.db import models

from tenants.models import Tenant


class Especialidad(models.Model):
    nombre = models.CharField(max_length=80, unique=True)

    class Meta:
        verbose_name_plural = "Especialidades"

    def __str__(self):
        return self.nombre


DIAS_SEMANA = [
    ("lun", "Lunes"), ("mar", "Martes"), ("mie", "Miércoles"),
    ("jue", "Jueves"), ("vie", "Viernes"), ("sab", "Sábado"), ("dom", "Domingo"),
]


class Barbero(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="barberos")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="barbero"
    )
    nombre = models.CharField(max_length=150)
    foto = models.ImageField(upload_to="barberos/", blank=True, null=True)
    especialidades = models.ManyToManyField(Especialidad, blank=True, related_name="barberos")
    rating_promedio = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    disponibilidad_semanal = models.JSONField(
        default=dict, blank=True,
        help_text='Ej: {"lun": ["10:00", "19:00"], "mar": ["10:00", "19:00"]}',
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def recalcular_rating(self):
        from django.db.models import Avg
        promedio = self.resenas.aggregate(avg=Avg("rating"))["avg"] or 0
        self.rating_promedio = round(promedio, 2)
        self.save(update_fields=["rating_promedio"])
        return self.rating_promedio
