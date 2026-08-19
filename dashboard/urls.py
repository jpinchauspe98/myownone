from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.kpis, name="kpis"),
    path("peluqueros/", views.ranking_peluqueros, name="ranking_peluqueros"),
    path("turnos/", views.turnos_list, name="turnos"),
    path("clientes/", views.clientes_list, name="clientes"),
    path("clientes/<int:cliente_id>/", views.cliente_detalle, name="cliente_detalle"),
    path("productos/", views.productos_panel, name="productos"),
    path("productos/vender/", views.registrar_venta, name="registrar_venta"),
    path("resenas/", views.resenas_list, name="resenas"),
    path("whatsapp/", views.mensajes_whatsapp, name="whatsapp"),
    path("login/", views.login_salon, name="login"),
    path("logout/", views.logout_salon, name="logout"),
]
