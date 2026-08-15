from django.db import models

from tenants.models import Tenant
from appointments.models import Turno


class MensajeWhatsApp(models.Model):
    """Log de mensajes entrantes/salientes. El webhook y la state machine de
    la conversación se implementan en Fase 2 (Meta WhatsApp Cloud API).
    """

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
