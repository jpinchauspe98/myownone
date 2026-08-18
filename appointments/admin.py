from django.contrib import admin

from .models import Cliente, Turno, Venta


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "telefono", "tenant")
    search_fields = ("nombre", "telefono")
    list_filter = ("tenant",)


@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = ("fecha_hora", "tenant", "cliente", "barbero", "servicio", "estado", "monto", "canal_origen")
    list_filter = ("tenant", "estado", "canal_origen", "barbero")
    date_hierarchy = "fecha_hora"
    search_fields = ("cliente__nombre", "cliente__telefono")


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("creado", "tenant", "producto", "cantidad", "total", "cliente", "barbero")
    list_filter = ("tenant", "producto", "barbero")
    date_hierarchy = "creado"
    search_fields = ("cliente__nombre", "producto__nombre")
