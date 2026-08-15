import functools
import secrets

from django.http import JsonResponse

from tenants.models import Tenant


def con_tenant_autenticado(view_func):
    """Resuelve el tenant por slug y exige un API key válido en el header
    Authorization: Bearer <api_key> (o X-Api-Key). Pensado para que
    integraciones externas (Forja u otro bot con LLM) llamen esta API como
    'tools' sin necesitar sesión de Django."""

    @functools.wraps(view_func)
    def wrapper(request, slug, *args, **kwargs):
        tenant = Tenant.objects.filter(slug=slug, activo=True).first()
        if tenant is None:
            return JsonResponse({"error": "salon_no_encontrado"}, status=404)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[len("Bearer "):].strip()
        else:
            api_key = request.headers.get("X-Api-Key", "").strip()

        if not api_key or not secrets.compare_digest(api_key, tenant.api_key):
            return JsonResponse({"error": "no_autorizado"}, status=401)

        return view_func(request, tenant, *args, **kwargs)

    return wrapper
