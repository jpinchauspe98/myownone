from django.contrib import admin

from .models import CategoriaServicio, Servicio, Producto, Promocion


@admin.register(CategoriaServicio)
class CategoriaServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tenant")
    list_filter = ("tenant",)


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tenant", "categoria", "precio", "duracion_min", "activo")
    list_filter = ("tenant", "categoria", "activo")
    search_fields = ("nombre",)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tenant", "precio", "stock", "activo")
    list_filter = ("tenant", "activo")
    search_fields = ("nombre",)


@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ("tenant", "tipo", "producto", "servicio", "vigencia_desde", "vigencia_hasta", "activo")
    list_filter = ("tenant", "tipo", "activo")
