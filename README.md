# SaaS de turnos para peluquerías (multi-tenant / white-label)

MVP construido desde cero en Django (sin depender de ningún esqueleto de
terceros — ver nota de licencia más abajo). Sigue el roadmap por fases
definido para el proyecto. `LEOLEIVA` es el primer salón cargado como
prueba, pero el sistema es multi-tenant desde el modelo de datos: un solo
deploy sirve a todos los salones, cada uno aislado del resto (ver
"Multi-tenant / white-label" más abajo) — el objetivo es poder prospectar
y dar de alta clientes nuevos sin desplegar nada por cliente.

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
- **Bot de WhatsApp por reglas fijas (Meta Cloud API)**: conversación de
  reserva con menús numerados, recordatorios 24hs/2hs antes del turno y
  solicitud de reseña 2hs después de completado. Funciona, pero es rígido
  ("respondé 1, 2 o 3") — no se recomienda como bot de cara al cliente.
- **API de "tools" para Forja**: en vez de seguir puliendo el bot de
  reglas, el salón puede conectar [Forja](https://forjabots.com) (un bot
  con LLM real, self-hosted en Cloudflare) para que la conversación sea
  natural, y Forja llama a esta API de Django para consultar
  disponibilidad y reservar. Es el camino recomendado para una
  conversación humana — ver detalle más abajo.
- **Multi-tenant / white-label**: cada salón tiene su propio login al
  panel (no ve el de otros salones), su propio color de marca, y un
  comando (`crear_salon`) para dar de alta un cliente nuevo en un paso.
  Ver detalle más abajo.

Todavía **no** está resuelto el pago total al finalizar el servicio, las
promociones activas en el flujo de reserva, ni el onboarding 100%
self-service (que el dueño cargue sus propios peluqueros/servicios sin
tocar `/admin/` — eso es Fase 3).

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

- Admin (superadmin, ve todos los salones): `/admin/`
- Mini-web pública de reservas: `/salones/leoleiva/`
- Panel del dueño del salón (login propio, sólo ve SU salón): `/panel/leoleiva/`
- Dejar reseña de un turno completado: `/salones/leoleiva/turno/<id>/resena/`

El seed no crea un usuario propietario para el panel de LEOLEIVA. Para
probarlo, creá un usuario y agregalo a `Tenant.propietarios` desde
`/admin/` → Tenant → "Acceso al panel" (o por shell:
`Tenant.objects.get(slug="leoleiva").propietarios.add(user)`). Para un
salón nuevo de cero, `crear_salon` hace las dos cosas de una — ver la
sección de abajo.

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
| `whatsapp_bot` | Bot de reglas fijas (Meta Cloud API): webhook, state machine, recordatorios y solicitud de reseñas |
| `dashboard` | KPIs de facturación y ranking de peluqueros por rating |
| `webbooking` | Mini-web pública: elegir servicio → peluquero → horario → confirmar |
| `api` | API de "tools" autenticada por API key, para bots externos con LLM (ej. Forja) |

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

## Bot de WhatsApp por reglas fijas (Meta Cloud API)

> Este bot funciona pero es un árbol de menús numerados, no una
> conversación natural. Para eso está la sección **"API de tools para
> Forja"** más abajo, que es el camino recomendado. Esta sección queda
> documentada por si se prefiere no depender de un servicio externo.

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

## API de "tools" para Forja (bot con LLM real)

El bot de reglas fijas de arriba responde bien pero suena a máquina.
[Forja](https://forjabots.com) es un bot con un modelo de lenguaje real
(Claude/GPT) que corre aparte, self-hosted en tu propio Cloudflare — no
es algo que se despliegue desde este repo. Forja se encarga de la
conversación (entender lenguaje natural, no sólo "respondé 1 o 2") y le
pega por HTTP a esta API cada vez que necesita consultar servicios,
peluqueros, horarios libres o crear una reserva. Django sigue siendo la
única fuente de verdad de turnos, precios y disponibilidad — Forja nunca
inventa un horario, siempre pregunta.

**Setup (del lado de Forja, no de este repo):** desplegar Forja siguiendo
su propia guía (`npx forjabot init` con Claude Code, o manual con
`wrangler`), y ahí cargar como "tools" los endpoints de abajo. No pude
leer la guía completa de Forja desde este entorno (su web está bloqueada
por la política de red de la sandbox), así que puede que los nombres de
campos que Forja pide en su dashboard no sean idénticos a los de acá —
la forma y la lógica de cada endpoint sí están resueltas y probadas.

### Autenticación

Cada salón tiene su propio `api_key` (se genera solo al crear el
`Tenant`, visible en `/admin/` → Tenant → "Integraciones externas").
Todos los endpoints van con:

```
Authorization: Bearer <api_key-del-salon>
```

Base URL: `https://<tu-dominio>/api/v1/<slug-del-salon>/`

### Endpoints (tools)

**1. Listar servicios**
`GET /api/v1/<slug>/servicios/`
```json
{"servicios": [{"id": 2, "nombre": "Corte clásico", "precio": 8000.0, "duracion_min": 30, "categoria": "Cortes"}]}
```

**2. Listar peluqueros**
`GET /api/v1/<slug>/peluqueros/`
```json
{"peluqueros": [{"id": 2, "nombre": "Leo Leiva", "rating_promedio": 4.4, "especialidades": ["Fade", "Clásico"]}]}
```

**3. Consultar horarios libres**
`GET /api/v1/<slug>/horarios-disponibles/?servicio_id=2&peluquero_id=2`
(`peluquero_id` es opcional: sin él, o con `peluquero_id=primero_disponible`, elige el de mejor rating)
```json
{"peluquero_id": 2, "peluquero_nombre": "Leo Leiva", "dias": [
  {"fecha": "2026-08-15", "horarios": [{"fecha_hora": "2026-08-15T17:00:00-03:00", "hora": "17:00"}]}
]}
```

**4. Crear turno**
`POST /api/v1/<slug>/turnos/`
```json
{"servicio_id": 2, "peluquero_id": 2, "fecha_hora": "2026-08-15T17:00:00-03:00", "cliente_nombre": "Marina", "cliente_telefono": "+5491166667777"}
```
`peluquero_id` es opcional (mismo criterio que arriba). Si el salón tiene
la seña activada, la respuesta trae `requiere_pago: true` y `link_pago`
(el bot le pasa ese link al cliente); si no, el turno queda `confirmado`
directo. Si falla la generación del link de pago, responde `502` y no
crea el turno — no quedan reservas fantasma.

**5. Estado de un turno**
`GET /api/v1/<slug>/turnos/<turno_id>/` — para que el bot confirme si la
seña ya se acreditó antes de decirle al cliente que está todo listo.

**6. Cancelar un turno**
`POST /api/v1/<slug>/turnos/<turno_id>/cancelar/` — `409` si ya estaba
completado o cancelado.

Todos los errores devuelven JSON con una clave `"error"` (ej.
`{"error": "servicio_no_encontrado"}`) y el código HTTP correspondiente
(400/401/404/409/502), para que el LLM de Forja pueda decidir qué decirle
al cliente en vez de romperse con una excepción.

**Probado en esta sesión** con `curl` autenticado: los 6 endpoints, el
rechazo sin API key o con una inválida (401), validaciones de campos
faltantes y fecha pasada (400), servicio/peluquero inexistente (404),
doble cancelación (409), y el caso de seña con token de Mercado Pago
inválido (502, sin turno huérfano). No se probó contra una instancia real
de Forja por no tener acceso a una en este entorno — el contrato HTTP de
cada endpoint sí quedó verificado de punta a punta.

**Sobre el bot de reglas fijas:** si se conecta Forja, hay que apuntar el
webhook de Meta a la URL de Forja en vez de
`/whatsapp/<slug>/webhook/` de Django (Meta sólo manda los mensajes a una
URL por número). El bot de reglas de este repo simplemente deja de
recibir tráfico — no hace falta borrar nada, ni hay conflicto entre los
dos.

## Multi-tenant / white-label

Un solo deploy sirve a todos los salones — no hay que clonar el repo ni
desplegar nada por cliente nuevo. Cada salón es una fila `Tenant` con su
propio slug, su propio color de marca, sus propios datos, y (esto es lo
que lo hace realmente entregable a un cliente) su **propio login al
panel** que no ve nada de los demás salones.

### Aislamiento entre salones

Antes de esta vuelta, el panel del dueño (`/panel/<slug>/`) sólo
chequeaba `is_staff` — cualquier usuario staff podía entrar al panel de
CUALQUIER salón cambiando el slug en la URL. Se corrigió:

- `Tenant.propietarios` (M2M a `User`) define quién puede administrar ese
  salón puntual.
- El panel tiene su login propio en `/panel/<slug>/login/` (branded con
  el nombre y color del salón, no la pantalla genérica de Django admin) —
  un dueño nunca necesita ni ve `/admin/`.
- Un superusuario sigue viendo cualquier panel (para vos, como dueño de
  la plataforma); un propietario normal sólo el suyo. Si intenta entrar
  al de otro salón, `403`.

**Probado en esta sesión:** creé un segundo salón de prueba
(`barberia-test-2`) con su propio dueño, confirmé que ese usuario puede
entrar a su panel pero recibe `403` al intentar `/panel/leoleiva/`, y que
el superusuario sigue viendo ambos paneles sin problema.

### Branding por salón

`Tenant.color_primario` (hex) reemplaza el rojo hardcodeado en la
mini-web y el panel — cada salón puede tener su propio color de marca
desde `/admin/`. Probado: un salón nuevo con color `#1e88e5` muestra la
mini-web y los botones en azul en vez del rojo por defecto, sin tocar
ninguna plantilla.

### Alta rápida de un salón nuevo (para prospectar)

```bash
python manage.py crear_salon \
  --nombre "Barbería del Centro" \
  --username barberia-del-centro_owner \
  --whatsapp "+5491100001111" \
  --color "#1e88e5"
```

Esto crea el `Tenant` (slug autogenerado del nombre si no se pasa
`--slug`) y un usuario propietario listo para entrar a
`/panel/<slug>/login/` — si no se pasa `--password`, genera una
aleatoria y la muestra en pantalla junto con las URLs del salón. Con eso
en mano ya podés mandarle el link al cliente. **Falta cargar a mano**
(no lo hace el comando, a propósito — cada salón es distinto):
peluqueros y servicios desde `/admin/`, y si corresponde, WhatsApp Cloud
API / Mercado Pago / la API key para Forja.

### Qué datos pedirle a cada peluquería antes de darle el link

- Nombre del salón, dirección, horario de apertura/cierre
- Lista de peluqueros (nombre, foto opcional, especialidades)
- Lista de servicios con precio y duración
- Color de marca (o se usa el rojo por defecto)
- Si van a cobrar seña: % de seña y su cuenta de Mercado Pago
- Si van a usar WhatsApp: número de WhatsApp Business (para el bot de
  reglas fijas hace falta además el Phone Number ID y access token de
  Meta; para Forja, la `api_key` del salón que ya se genera sola)

### Qué NO está resuelto todavía para self-service completo

Hoy cargar peluqueros/servicios/horarios sigue siendo trabajo tuyo (o del
cliente) en `/admin/` — no hay un formulario propio en el panel para que
el dueño del salón edite eso sin tocar el admin de Django. Eso es
exactamente la Fase 3 del roadmap original ("onboarding self-service de
nuevos salones"); por ahora el flujo es: vos cargás los datos del salón
al cerrar la venta, y le das el link de login ya armado.

## Próximos pasos (no arrancar sin validar lo anterior con el cliente real)

- Terminar Fase 2: promociones activas en el flujo de reserva/pago (web y WhatsApp) + pago total al finalizar el servicio.
- Fase 3: multi-tenant self-service, panel super-admin, facturación SaaS.
