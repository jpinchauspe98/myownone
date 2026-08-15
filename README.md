# LEOLEIVA — SaaS de turnos para peluquerías

MVP construido desde cero en Django (sin depender de ningún esqueleto de
terceros — ver nota de licencia más abajo). Sigue el roadmap por fases
definido para el proyecto.

## Estado actual: Fase 0 + Fase 1 completas

- **Fase 0**: proyecto Django armado, modelos con `tenant_id`, admin
  funcionando (se puede crear un salón, un peluquero y un servicio a mano).
- **Fase 1**: elegir peluquero al reservar (o "primero disponible"),
  reseñas ligadas 1 a 1 al peluquero que atendió, dashboard de KPIs con
  facturación total y desglosada por peluquero/servicio.

Todavía **no** están implementados el bot de WhatsApp ni Mercado Pago
(Fase 2) ni el multi-tenant real por subdominio (Fase 3) — los modelos
(`MensajeWhatsApp`, `Pago`) ya existen para no tener que migrar de nuevo,
pero la lógica de negocio de esas fases no se construyó todavía.

## Nota sobre el punto de partida

El prompt original pedía clonar `AbdullahBakir97/Barber-Salon` como
"MIT license, uso comercial permitido". Al revisar el `LICENSE` real del
repo, es **propietario** ("All rights reserved", licenciado a un cliente
específico, sin derecho a redistribuir/sublicenciar) — no es MIT y no
habilita uso comercial por terceros. Por eso el proyecto se construyó
desde cero con código propio, sin usar ese repo.

## Setup local

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py seed_leoleiva   # datos demo: salón LEOLEIVA, 3 peluqueros, 4 servicios, turnos y reseñas
python manage.py runserver
```

- Admin: `/admin/`
- Mini-web pública de reservas: `/salones/leoleiva/`
- Panel del dueño (requiere usuario staff): `/panel/leoleiva/` y `/panel/leoleiva/peluqueros/`
- Dejar reseña de un turno completado: `/salones/leoleiva/turno/<id>/resena/`

Por defecto usa SQLite (`db.sqlite3`). Para Postgres, cambiar `DATABASES`
en `config/settings.py`.

## Estructura de apps

| App | Responsabilidad |
|---|---|
| `tenants` | Modelo `Tenant` (salón) + middleware de resolución por slug |
| `staff` | `Barbero`, `Especialidad`, rating y disponibilidad semanal |
| `catalog` | `Servicio`, `CategoriaServicio`, `Producto`, `Promocion` |
| `appointments` | `Cliente`, `Turno` (con validación de fechas pasadas y horario del salón) |
| `reviews` | `Resena`, ligada al `Turno` y por lo tanto al `Barbero` específico |
| `payments` | `Pago` (modelo listo, integración Mercado Pago pendiente — Fase 2) |
| `whatsapp_bot` | `MensajeWhatsApp` (log, webhook y state machine pendientes — Fase 2) |
| `dashboard` | KPIs de facturación y ranking de peluqueros por rating |
| `webbooking` | Mini-web pública: elegir servicio → peluquero → horario → confirmar |

## Criterios de aceptación de Fase 1 (verificados)

- [x] El cliente ve los peluqueros disponibles y elige uno específico (o
      "primero disponible") al reservar.
- [x] Al marcar un turno como "completado", se habilita dejar una reseña
      asociada a ESE peluquero (no genérica del salón) — `Resena.turno`
      es 1 a 1 y denormaliza `barbero` desde el turno.
- [x] El dueño ve `/panel/<slug>/` con facturación total del período y
      desglosada por peluquero y por servicio, más ranking de peluqueros
      con alerta si el rating cae debajo del umbral configurable por
      tenant (`Tenant.umbral_alerta_rating`).

## Próximos pasos (no arrancar sin validar Fase 1 con el cliente real)

- Fase 2: bot de WhatsApp (Meta Cloud API) + checkout Mercado Pago + promociones activas en el flujo de reserva.
- Fase 3: multi-tenant self-service, panel super-admin, facturación SaaS.
