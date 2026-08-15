from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse
from django.utils import timezone

from appointments.models import Turno
from whatsapp_bot.client import enviar_mensaje, WhatsAppNoConfigurado


class Command(BaseCommand):
    help = (
        "Pide una reseña por WhatsApp a los clientes cuyo turno se marcó "
        "'completado' hace 2hs o más. Pensado para correrse cada 10-15 "
        "minutos vía cron."
    )

    def handle(self, *args, **options):
        limite = timezone.now() - timezone.timedelta(hours=2)
        turnos = Turno.objects.filter(
            estado=Turno.Estado.COMPLETADO, resena_solicitada=False,
            completado_en__isnull=False, completado_en__lte=limite,
        ).select_related("tenant", "cliente", "barbero")

        enviados = 0
        for turno in turnos:
            link = settings.SITE_BASE_URL + reverse("reviews:dejar_resena", args=[turno.tenant.slug, turno.id])
            texto = (
                f"¡Gracias por venir a {turno.tenant.nombre}! ¿Nos dejás una reseña de tu corte "
                f"con {turno.barbero.nombre}? {link}"
            )
            try:
                enviar_mensaje(turno.tenant, turno.cliente.telefono, texto, turno=turno)
            except WhatsAppNoConfigurado:
                continue
            turno.resena_solicitada = True
            turno.save(update_fields=["resena_solicitada"])
            enviados += 1

        self.stdout.write(self.style.SUCCESS(f"Solicitudes de reseña enviadas: {enviados}"))
