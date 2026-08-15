# LEOLEIVA — SaaS de turnos para peluquerías

MVP construido desde cero en Django (sin depender de ningún esqueleto de
terceros — ver nota de licencia más abajo). Sigue el roadmap por fases
definido para el proyecto.

## Estado actual: Fase 0, Fase 1 y bot de WhatsApp (Fase 2 en curso)

- **Fase 0**: proyecto Django armado, modelos con `tenant_id`, admin
  funcionando (se puede crear un salón, un peluquero y un servicio a mano).
- **Fase 1**: elegir peluquero al reservar (o "primero disponible"),
  reseñas ligadas 1 a 1 al peluquero que atendió, dashboard de KPIs con
  facturación total y desglosada por peluquero/servicio.
- **Seña con Mercado Pago**: si el salón tiene `sena_habilitada` y un
  `mp_access_token` cargado, reservar (web o WhatsApp) redirige al
  cliente al link de pago de Checkout Pro antes de confirmar el turno,
  para reducir el ausentismo. Ver detalle más abajo.
- **Bot de WhatsApp (Meta Cloud API)**: conversación completa de reserva
  (saludo → servicio → peluquero → horario → confirmar → seña si
  corresponde), recordatorios 24hs/2hs antes del turno y solicitud de
  reseña 2hs después de completado. Ver detalle más abajo.

Todavía **no** están implementados el pago total al finalizar el
servicio, las promociones activas en el flujo de reserva, ni el
multi-tenant real por subdominio (Fase 3).

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
| `payments` | `Pago`, integración Checkout Pro (seña al reservar) + webhook |
| `whatsapp_bot` | Bot de reservas (Meta Cloud API): webhook, state machine, recordatorios y solicitud de reseñas |
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

## Seña con Mercado Pago

Cada salón cobra con su propia cuenta de Mercado Pago (multi-tenant desde
el día uno, la plataforma no procesa el dinero de terceros). Para
activarla en un salón, desde `/admin/` en el `Tenant` correspondiente:

1. Cargar `mp_access_token` (el access token de la cuenta de Mercado Pago del salón — Production o Test).
2. Activar `sena_habilitada` y ajustar `sena_porcentaje` (por defecto 30%).

Con eso activo, al confirmar el turno en la mini-web el cliente es
redirigido al Checkout Pro de Mercado Pago para pagar la seña; recién ahí
el turno pasa a `confirmado` (antes queda en `pendiente`). El webhook
(`/salones/<slug>/pagos/webhook/`) y la página de retorno
(`/salones/<slug>/pagos/retorno/<turno_id>/`) confirman el pago aunque el
cliente cierre la pestaña de Mercado Pago antes de volver.

Si `sena_habilitada` está en `True` pero no hay `mp_access_token`
cargado, el turno se confirma directo sin pedir seña (no bloquea reservas
por una config a medio terminar). Si el token está cargado pero es
inválido o la API de Mercado Pago falla, no se crea el turno y se le pide
al cliente reintentar — no se pierden reservas por errores silenciosos.

**No se pudo probar el pago real end-to-end en esta sesión** (no hay
credenciales de Mercado Pago disponibles en este entorno) — sí se probó
el flujo normal sin seña (regresión), el aviso del monto de la seña antes
de confirmar, y el manejo de error cuando el token es inválido (no queda
ningún turno huérfano en la base). Antes de ir a producción con un salón
real, probar el circuito completo con credenciales de Test de Mercado
Pago.

## Bot de WhatsApp (Meta Cloud API)

Cada salón tiene su propio número de WhatsApp Business y su propia app de
Meta (no hay un único bot compartido entre tenants). Para activarlo,
desde `/admin/` en el `Tenant` correspondiente:

1. Crear una app de Meta en [developers.facebook.com](https://developers.facebook.com/) con el producto **WhatsApp**, y ahí conseguir el **Phone Number ID** y un **access token permanente** (System User token, no el temporal de 24hs de la vista rápida).
2. Cargar `whatsapp_phone_number_id` y `whatsapp_access_token` en el `Tenant`.
3. Inventar y cargar un `whatsapp_verify_token` (cualquier string propio).
4. En Meta for Developers → WhatsApp → Configuration, configurar el
   webhook con URL `https://<tu-dominio>/whatsapp/<slug-del-salon>/webhook/`
   y el mismo `whatsapp_verify_token`; suscribirse al campo `messages`.

Con eso, escribirle "hola" al número del salón dispara la conversación:
elige servicio → elige peluquero (o "0" para primero disponible) → elige
horario (lista los próximos 8 libres) → nombre (sólo si es cliente nuevo)
→ confirma con "1"/"2" → si el salón tiene la seña activada, el bot manda
el link de pago de Mercado Pago; si no, confirma el turno directo. La
lógica de la conversación vive en `whatsapp_bot/conversation.py`
(`procesar_mensaje_entrante`), reutilizando el mismo cálculo de horarios
libres (`appointments/services.py`) y la misma integración de Mercado
Pago que usa la mini-web — no hay dos implementaciones del mismo negocio.

**Recordatorios y solicitud de reseñas** corren como comandos de
management pensados para cron (no hay Celery en este MVP, sería
sobreingeniería para el volumen de un salón):

```bash
python manage.py enviar_recordatorios   # turnos confirmados a 24hs y a 2hs de la hora del turno
python manage.py solicitar_resenas      # turnos completados hace 2hs o más, sin reseña pedida todavía
```

En producción (Railway/Render), programar ambos cada 10-15 minutos. Cada
uno es idempotente: usa los flags `recordatorio_24h_enviado`,
`recordatorio_2h_enviado` y `resena_solicitada` de `Turno` para no
reenviar dos veces.

**Probado en esta sesión sin credenciales reales de Meta** (no hay una
app de WhatsApp Business disponible en este entorno): la conversación
completa se probó llamando directamente a `procesar_mensaje_entrante`
(saludo → servicio → peluquero → horario → nombre → confirmar, terminó
creando el `Turno` con `canal_origen=whatsapp` correctamente) y el
webhook HTTP se probó con un payload real de Meta contra
`/whatsapp/leoleiva/webhook/` (handshake de verificación GET y mensaje
entrante POST, ambos funcionando). Lo que no se pudo probar es el envío
real de mensajes salientes contra `graph.facebook.com` — durante las
pruebas apareció un bug real (una falla de red al enviar tumbaba todo el
comando de recordatorios a mitad de camino) que ya está corregido: los
errores de conexión ahora se loguean y no interrumpen el resto del batch,
igual que los errores HTTP de la propia API de Meta. Antes de producción,
probar el envío real con una app de Meta y un número de prueba.

## Próximos pasos (no arrancar sin validar lo anterior con el cliente real)

- Terminar Fase 2: promociones activas en el flujo de reserva/pago (web y WhatsApp) + pago total al finalizar el servicio.
- Fase 3: multi-tenant self-service, panel super-admin, facturación SaaS.
