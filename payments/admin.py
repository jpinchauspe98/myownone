from django.contrib import admin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("turno", "concepto", "monto", "estado", "neto_salon", "mp_payment_id", "creado")
    list_filter = ("estado", "concepto")
    search_fields = ("mp_payment_id", "mp_preference_id")
