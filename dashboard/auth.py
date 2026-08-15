import functools

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from tenants.models import Tenant


def puede_administrar(user, tenant):
    if not user.is_authenticated:
        return False
    return user.is_superuser or tenant.propietarios.filter(id=user.id).exists()


def propietario_o_superadmin_required(view_func):
    """Reemplaza a @staff_member_required: en vez de dejar entrar a
    cualquier usuario is_staff (que vería el panel de TODOS los salones),
    sólo deja pasar a un superusuario o a un propietario de ESE tenant
    puntual. Redirige al login propio del panel (no al de /admin/) si hace
    falta, y le pasa el `tenant` ya resuelto a la vista en vez del slug."""

    @functools.wraps(view_func)
    def wrapper(request, slug, *args, **kwargs):
        tenant = get_object_or_404(Tenant, slug=slug)

        if not request.user.is_authenticated:
            login_url = reverse("dashboard:login", args=[slug])
            return redirect(f"{login_url}?next={request.path}")

        if not puede_administrar(request.user, tenant):
            return HttpResponseForbidden("Tu usuario no tiene acceso al panel de este salón.")

        return view_func(request, tenant, *args, **kwargs)

    return wrapper
