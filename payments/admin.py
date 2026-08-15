from django.contrib import admin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("turno", "monto", "estado", "neto_salon", "creado")
    list_filter = ("estado",)
