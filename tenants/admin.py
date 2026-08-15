from django.contrib import admin

from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug", "plan", "activo", "whatsapp_number", "sena_habilitada")
    list_filter = ("plan", "activo", "sena_habilitada")
    prepopulated_fields = {"slug": ("nombre",)}
    search_fields = ("nombre", "slug")
    readonly_fields = ("api_key",)
    fieldsets = (
        (None, {"fields": ("nombre", "slug", "plan", "activo", "direccion")}),
        ("WhatsApp Cloud API", {"fields": (
            "whatsapp_number", "whatsapp_phone_number_id", "whatsapp_access_token", "whatsapp_verify_token",
        )}),
        ("Horario", {"fields": ("horario_apertura", "horario_cierre")}),
        ("Mercado Pago", {"fields": ("mp_access_token", "sena_habilitada", "sena_porcentaje")}),
        ("Reseñas", {"fields": ("umbral_alerta_rating",)}),
        ("Integraciones externas (ej. Forja)", {"fields": ("api_key",)}),
    )
