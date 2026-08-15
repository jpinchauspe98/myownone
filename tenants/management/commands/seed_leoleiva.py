import datetime
import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from tenants.models import Tenant
from staff.models import Barbero, Especialidad
from catalog.models import CategoriaServicio, Servicio, Producto, Promocion
from appointments.models import Cliente, Turno
from reviews.models import Resena


class Command(BaseCommand):
    help = "Siembra datos demo para el salón LEOLEIVA (Fase 1)."

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(
            slug="leoleiva",
            defaults=dict(nombre="LEOLEIVA", whatsapp_number="+5491122334455", plan=Tenant.Plan.TRIAL),
        )

        especialidades = {
            nombre: Especialidad.objects.get_or_create(nombre=nombre)[0]
            for nombre in ["Fade", "Barba", "Color", "Clásico"]
        }

        barberos_data = [
            ("Leo Leiva", ["Fade", "Clásico"]),
            ("Nico Suárez", ["Barba", "Color"]),
            ("Fede Gómez", ["Fade", "Barba"]),
        ]
        barberos = []
        for nombre, esps in barberos_data:
            b, _ = Barbero.objects.get_or_create(tenant=tenant, nombre=nombre)
            b.especialidades.set([especialidades[e] for e in esps])
            barberos.append(b)

        cat_cortes, _ = CategoriaServicio.objects.get_or_create(tenant=tenant, nombre="Cortes")
        cat_barba, _ = CategoriaServicio.objects.get_or_create(tenant=tenant, nombre="Barba")

        servicios_data = [
            ("Corte clásico", cat_cortes, 8000, 30),
            ("Corte + Fade", cat_cortes, 10000, 45),
            ("Arreglo de barba", cat_barba, 5000, 20),
            ("Corte + Barba", cat_barba, 12000, 50),
        ]
        servicios = []
        for nombre, cat, precio, dur in servicios_data:
            s, _ = Servicio.objects.get_or_create(
                tenant=tenant, nombre=nombre, defaults=dict(categoria=cat, precio=precio, duracion_min=dur)
            )
            servicios.append(s)

        producto, _ = Producto.objects.get_or_create(
            tenant=tenant, nombre="Cera moldeadora",
            defaults=dict(precio=6500, stock=20, descripcion="Fijación fuerte, terminación mate"),
        )
        hoy = timezone.localdate()
        Promocion.objects.get_or_create(
            tenant=tenant, producto=producto, tipo=Promocion.Tipo.PORCENTAJE,
            defaults=dict(valor=15, vigencia_desde=hoy, vigencia_hasta=hoy + datetime.timedelta(days=30)),
        )

        clientes_data = [("Juan Pérez", "+5491100000001"), ("Mora Díaz", "+5491100000002"),
                          ("Tomás Ruiz", "+5491100000003")]
        clientes = []
        for nombre, tel in clientes_data:
            c, _ = Cliente.objects.get_or_create(tenant=tenant, telefono=tel, defaults=dict(nombre=nombre))
            clientes.append(c)

        # turnos completados en el mes actual, para poblar el dashboard de KPIs
        creados = 0
        for i in range(12):
            barbero = random.choice(barberos)
            servicio = random.choice(servicios)
            cliente = random.choice(clientes)
            dias_atras = random.randint(1, 20)
            fecha_hora = timezone.now() - datetime.timedelta(days=dias_atras, hours=random.randint(0, 5))
            turno = Turno.objects.filter(
                tenant=tenant, cliente=cliente, barbero=barbero, fecha_hora=fecha_hora
            ).first()
            if turno:
                continue
            turno = Turno(
                tenant=tenant, cliente=cliente, barbero=barbero, servicio=servicio,
                fecha_hora=fecha_hora, estado=Turno.Estado.COMPLETADO,
                canal_origen=random.choice([Turno.Canal.WEB, Turno.Canal.WHATSAPP]),
                monto=servicio.precio,
            )
            turno.save()
            creados += 1
            if random.random() < 0.7 and not hasattr(turno, "resena"):
                Resena.objects.create(
                    turno=turno, tenant=tenant, barbero=barbero, cliente=cliente,
                    rating=random.choice([3, 4, 4, 5, 5]),
                    comentario="Muy buen servicio" if random.random() > 0.5 else "",
                )

        # un turno futuro pendiente para probar el flujo de reserva/cancelación
        Turno.objects.get_or_create(
            tenant=tenant, cliente=clientes[0], barbero=barberos[0], servicio=servicios[0],
            fecha_hora=timezone.now() + datetime.timedelta(days=2, hours=3),
            defaults=dict(estado=Turno.Estado.CONFIRMADO, canal_origen=Turno.Canal.WEB, monto=servicios[0].precio),
        )

        self.stdout.write(self.style.SUCCESS(
            f"Listo. Tenant={tenant.slug} barberos={len(barberos)} servicios={len(servicios)} turnos_nuevos={creados}"
        ))
