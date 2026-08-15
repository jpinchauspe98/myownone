import secrets

from django.db import models


def _generar_api_key():
    return secrets.token_urlsafe(32)


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
    whatsapp_phone_number_id = models.CharField(
        max_length=50, blank=True,
        help_text="Phone Number ID de Meta WhatsApp Cloud API (Meta for Developers → WhatsApp → API Setup)",
    )
    whatsapp_access_token = models.CharField(
        max_length=512, blank=True,
        help_text="Access token permanente de la app de Meta para enviar mensajes por este número",
    )
    whatsapp_verify_token = models.CharField(
        max_length=100, blank=True,
        help_text="Token propio (lo inventás vos) usado para verificar el webhook en Meta for Developers",
    )
    mp_access_token = models.CharField(
        max_length=255, blank=True,
        help_text="Access token (Production o Test) de la cuenta de Mercado Pago del salón",
    )
    sena_habilitada = models.BooleanField(
        default=False,
        help_text="Si está activo, el cliente debe pagar una seña por Mercado Pago para confirmar el turno",
    )
    sena_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=30,
        help_text="% del precio del servicio que se cobra como seña",
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
    api_key = models.CharField(
        max_length=64, unique=True, default=_generar_api_key, editable=False,
        help_text="Usada por integraciones externas (ej. Forja) para autenticarse contra la API de turnos de este salón",
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
