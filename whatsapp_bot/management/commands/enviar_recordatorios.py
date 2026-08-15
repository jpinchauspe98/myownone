from django.core.management.base import BaseCommand
from django.utils import timezone

from appointments.models import Turno
from appointments.services import formatear_fecha_hora
from whatsapp_bot.client import enviar_mensaje, WhatsAppNoConfigurado


class Command(BaseCommand):
    help = (
        "Envía recordatorios de turnos por WhatsApp 24hs y 2hs antes. "
        "Pensado para correrse cada 10-15 minutos vía cron."
    )

    def handle(self, *args, **options):
        ahora = timezone.now()
        enviados_24h = self._recordar(ahora, ventana=timezone.timedelta(hours=24), campo="recordatorio_24h_enviado",
                                       intro="Te recordamos tu turno para mañana")
        enviados_2h = self._recordar(ahora, ventana=timezone.timedelta(hours=2), campo="recordatorio_2h_enviado",
                                      intro="Te recordamos que tenés turno en 2hs")
        self.stdout.write(self.style.SUCCESS(f"Recordatorios 24h: {enviados_24h} | Recordatorios 2h: {enviados_2h}"))

    def _recordar(self, ahora, ventana, campo, intro):
        turnos = Turno.objects.filter(
            estado=Turno.Estado.CONFIRMADO, fecha_hora__gt=ahora, fecha_hora__lte=ahora + ventana,
            **{campo: False},
        ).select_related("tenant", "cliente", "barbero", "servicio")

        enviados = 0
        for turno in turnos:
            texto = (
                f"{intro}: *{turno.servicio.nombre}* con *{turno.barbero.nombre}* "
                f"el {formatear_fecha_hora(turno.fecha_hora)} en {turno.tenant.nombre}."
            )
            try:
                enviar_mensaje(turno.tenant, turno.cliente.telefono, texto, turno=turno)
            except WhatsAppNoConfigurado:
                continue
            setattr(turno, campo, True)
            turno.save(update_fields=[campo])
            enviados += 1
        return enviados
