from django.utils.deprecation import MiddlewareMixin

from .models import Tenant


class TenantResolutionMiddleware(MiddlewareMixin):
    """Resuelve el tenant activo a partir del slug en la URL: /salones/<slug>/...

    MVP mono-tenant: si no hay slug en el path, request.tenant queda en None
    y las vistas que lo necesiten (admin, dashboard) resuelven el tenant por
    el usuario logueado. Cuando se migre a multi-tenant real (Fase 3) esto
    se puede extender a resolución por subdominio.
    """

    def process_request(self, request):
        request.tenant = None
        parts = request.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "salones":
            slug = parts[1]
            request.tenant = Tenant.objects.filter(slug=slug, activo=True).first()
