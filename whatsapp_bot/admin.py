from django.contrib import admin

from .models import MensajeWhatsApp


@admin.register(MensajeWhatsApp)
class MensajeWhatsAppAdmin(admin.ModelAdmin):
    list_display = ("cliente_telefono", "direccion", "tenant", "timestamp")
    list_filter = ("tenant", "direccion")
