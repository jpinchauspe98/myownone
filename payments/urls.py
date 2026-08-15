from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("<slug:slug>/pagos/webhook/", views.webhook, name="webhook"),
    path("<slug:slug>/pagos/retorno/<int:turno_id>/", views.retorno, name="retorno"),
]
