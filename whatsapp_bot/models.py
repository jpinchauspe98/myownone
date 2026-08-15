from django.db import models

from tenants.models import Tenant
from appointments.models import Turno


class MensajeWhatsApp(models.Model):
    """Log de mensajes entrantes/salientes con Meta WhatsApp Cloud API."""

    class Direccion(models.TextChoices):
        IN = "in", "Entrante"
        OUT = "out", "Saliente"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="mensajes_whatsapp")
    cliente_telefono = models.CharField(max_length=20)
    direccion = models.CharField(max_length=3, choices=Direccion.choices)
    contenido = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    turno = models.ForeignKey(
        Turno, on_delete=models.SET_NULL, null=True, blank=True, related_name="mensajes_whatsapp"
    )

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.direccion} {self.cliente_telefono}: {self.contenido[:40]}"


class ConversacionWhatsApp(models.Model):
    """Estado de la conversación con un cliente por WhatsApp — la state
    machine del bot de reservas."""

    class Paso(models.TextChoices):
        INICIO = "inicio", "Inicio"
        SERVICIO = "servicio", "Esperando elegir servicio"
        PELUQUERO = "peluquero", "Esperando elegir peluquero"
        HORARIO = "horario", "Esperando elegir horario"
        NOMBRE = "nombre", "Esperando nombre del cliente"
        CONFIRMAR = "confirmar", "Esperando confirmación"
        FINALIZADO = "finalizado", "Conversación finalizada"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="conversaciones_whatsapp")
    telefono = models.CharField(max_length=20)
    paso = models.CharField(max_length=20, choices=Paso.choices, default=Paso.INICIO)
    contexto = models.JSONField(default=dict, blank=True)
    actualizado = models.DateTimeField(auto_now=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tenant", "telefono")

    def __str__(self):
        return f"{self.telefono} @ {self.tenant.slug} ({self.paso})"

    def reiniciar(self):
        self.paso = self.Paso.INICIO
        self.contexto = {}
        self.save(update_fields=["paso", "contexto"])
