from django.contrib import admin

from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug", "plan", "activo", "whatsapp_number")
    list_filter = ("plan", "activo")
    prepopulated_fields = {"slug": ("nombre",)}
    search_fields = ("nombre", "slug")
