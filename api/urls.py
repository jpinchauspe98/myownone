from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("<slug:slug>/servicios/", views.servicios, name="servicios"),
    path("<slug:slug>/peluqueros/", views.peluqueros, name="peluqueros"),
    path("<slug:slug>/horarios-disponibles/", views.horarios_disponibles, name="horarios_disponibles"),
    path("<slug:slug>/turnos/", views.crear_turno, name="crear_turno"),
    path("<slug:slug>/turnos/<int:turno_id>/", views.turno_detalle, name="turno_detalle"),
    path("<slug:slug>/turnos/<int:turno_id>/cancelar/", views.cancelar_turno, name="cancelar_turno"),
]
