from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.kpis, name="kpis"),
    path("peluqueros/", views.ranking_peluqueros, name="ranking_peluqueros"),
]
