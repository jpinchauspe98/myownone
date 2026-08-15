from django.urls import path

from . import views

app_name = "webbooking"

urlpatterns = [
    path("<slug:slug>/", views.salon_home, name="home"),
    path("<slug:slug>/reservar/", views.reservar, name="reservar"),
    path("<slug:slug>/reservar/confirmacion/<int:turno_id>/", views.confirmacion, name="confirmacion"),
]
