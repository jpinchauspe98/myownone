from django.contrib import admin

from .models import ConversacionWhatsApp, MensajeWhatsApp


@admin.register(MensajeWhatsApp)
class MensajeWhatsAppAdmin(admin.ModelAdmin):
    list_display = ("cliente_telefono", "direccion", "tenant", "timestamp")
    list_filter = ("tenant", "direccion")
    search_fields = ("cliente_telefono", "contenido")


@admin.register(ConversacionWhatsApp)
class ConversacionWhatsAppAdmin(admin.ModelAdmin):
    list_display = ("telefono", "tenant", "paso", "actualizado")
    list_filter = ("tenant", "paso")
    search_fields = ("telefono",)
