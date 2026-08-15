from django.contrib import admin

from .models import Resena


@admin.register(Resena)
class ResenaAdmin(admin.ModelAdmin):
    list_display = ("barbero", "cliente", "rating", "fecha", "tenant")
    list_filter = ("tenant", "barbero", "rating")
    search_fields = ("comentario",)
