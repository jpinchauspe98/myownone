from django.contrib import admin

from .models import Barbero, Especialidad


@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    search_fields = ("nombre",)


@admin.register(Barbero)
class BarberoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tenant", "rating_promedio", "activo")
    list_filter = ("tenant", "activo", "especialidades")
    search_fields = ("nombre",)
    filter_horizontal = ("especialidades",)
