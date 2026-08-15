from django.db import models


class Tenant(models.Model):
    """Un salón/peluquería cliente de la plataforma SaaS."""

    class Plan(models.TextChoices):
        TRIAL = "trial", "Prueba"
        BASICO = "basico", "Básico"
        PRO = "pro", "Pro"

    nombre = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True)
    whatsapp_number = models.CharField(
        max_length=20, blank=True,
        help_text="Número de WhatsApp Business del salón, formato E.164",
    )
    mp_access_token = models.CharField(
        max_length=255, blank=True,
        help_text="Access token de Mercado Pago del salón (Fase 2)",
    )
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.TRIAL)
    activo = models.BooleanField(default=True)
    direccion = models.CharField(max_length=255, blank=True)
    horario_apertura = models.TimeField(default="09:00")
    horario_cierre = models.TimeField(default="20:00")
    umbral_alerta_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=3.5,
        help_text="Si el rating promedio de un peluquero cae debajo de este valor, se genera una alerta",
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
