# Guía final de despliegue en Render

Esta guía describe el estado técnico actual de `SIGA_SUIZA_2026` y el procedimiento recomendado para desplegarlo en Render. No contiene secretos ni URLs definitivas inventadas: los valores finales se configuran en el panel de Render.

## 1. Objetivo y reglas

Dejar el proyecto preparado para Render sin cambiar la lógica de negocio, los endpoints, las tablas, los módulos ni los modelos existentes.

Reglas vigentes:

1. No hacer `git commit`.
2. No hacer `git push`.
3. No borrar archivos importantes.
4. No eliminar Docker Compose ni la base de datos local.
5. No importar el dump automáticamente en el arranque.
6. No poner contraseñas, tokens ni URLs secretas en archivos versionados.
7. No crear servicios públicos separados para los módulos internos.
8. No agregar `render.yaml`: la configuración final se define en el panel de Render.

## 2. Arquitectura final

```text
Render Static Site (siga_frontend)
        ↓ HTTPS
Render Web Service Docker (Core + 7 módulos internos)
        ↓ DATABASE_URL
Render PostgreSQL administrado
```

- Frontend: React + Vite 8 publicado como Static Site.
- Backend: FastAPI publicado como Web Service Docker usando el `Dockerfile` de la raíz.
- Base de datos: PostgreSQL administrado por Render.
- Microservicios: ejecutándose dentro del mismo contenedor del backend, en `127.0.0.1`.
- NATS: desactivado inicialmente; queda como capacidad opcional.
- Redis: no se utiliza inicialmente.
- pgAdmin es solo una herramienta de administración; no aloja la base.

## 3. Servicios que crear en Render

### 3.1 PostgreSQL

- Crear un PostgreSQL administrado en Render.
- Copiar la `DATABASE_URL` generada y cargarla como secreto del Web Service.
- No pegar esa URL en archivos del repositorio.

### 3.2 Backend Web Service

- Tipo: Docker.
- Root Directory: raíz del repositorio.
- Dockerfile: `Dockerfile`.
- Start Command: `sh ./start_railway.sh`.
- Health Check Path: `/health`.
- El contenedor escucha en `0.0.0.0:$PORT`.
- `start_railway.sh` levanta los 7 módulos internos, espera sus `/health` y después inicia el Core.
- No usar `--reload` cuando `ENVIRONMENT=production`.

### 3.3 Frontend Static Site

- Root Directory: `siga_frontend`.
- Build Command: `npm ci && npm run build`.
- Publish Directory: `dist` desde `siga_frontend` (`siga_frontend/dist` desde la raíz del repo).
- Requiere Node 22 o superior porque Vite 8 declara `engines.node >= 20.19 || >=22.12`; usar Node 22 para evitar avisos `EBADENGINE`.
- Agregar rewrite de SPA: `/*` → `/index.html`, status `200`.
- `VITE_API_URL` se lee en tiempo de build; cambiarlo exige rebuild/redeploy.

### 3.4 NATS

- No crear inicialmente.
- Si se necesita auditoría en tiempo real o entrega real de eventos, crear un servicio NATS privado y configurar `ENABLE_NATS=true` con `NATS_URL`.
- No publicar el puerto de NATS.

### 3.5 Otros

- No crear 7 Web Services para los módulos.
- No crear Redis para el despliegue inicial.
- No crear servicios adicionales salvo que aparezca una necesidad técnica real.

## 4. Puertos

### Producción Render

| Servicio | Puerto | Exposición |
|---|---:|---|
| Backend Core | `$PORT` | Público |
| `mod-usuarios` | 8001 | Interno `127.0.0.1` |
| `mod-planes-estudio` | 8002 | Interno `127.0.0.1` |
| `mod-programas-estudio` | 8005 | Interno `127.0.0.1` |
| `mod-gestion-academica` | 8006 | Interno `127.0.0.1` |
| `mod-auditoria` | 8007 | Interno `127.0.0.1` |
| `mod-evaluacion` | 8008 | Interno `127.0.0.1` |
| `mod-admision` | 8009 | Interno `127.0.0.1` |
| PostgreSQL Render | gestionado por Render | Interno/privado |
| NATS opcional | 4222 | Interno/privado |

### Desarrollo local

| Servicio | Puerto |
|---|---:|
| Frontend | `http://localhost:5173` |
| Backend | `http://localhost:8000` |
| PostgreSQL | `localhost:5433` |
| Redis | `localhost:6379` |
| NATS | `localhost:4222` |
| Módulos | `8001`, `8002`, `8005`, `8006`, `8007`, `8008`, `8009` |

## 5. Variables de entorno

### 5.1 Backend obligatorias

- `DATABASE_URL` — secreto; lo genera Render.
- `SECRET_KEY` — secreto; generar un valor seguro en Render.
- `ENVIRONMENT=production`.
- `PORT` — Render lo inyecta automáticamente.
- `FRONTEND_URL` — origen real del frontend.
- `CORS_ORIGINS` — lista separada por comas con los orígenes permitidos.
- `SKIP_MIGRATIONS=false` — al menos en el primer despliegue.

### 5.2 Backend opcionales recomendadas

- `DEBUG=false`.
- `DB_SSLMODE` — `disable`, `require`, `verify-ca` o `verify-full`; solo si no viene en `DATABASE_URL`.
- `PROGRAMAS_MODULE_URL` — default `http://127.0.0.1:8005`.
- `PLANES_MODULE_URL` — default `http://127.0.0.1:8002`.
- `ENABLE_NATS=false`.
- `NATS_URL` — solo si `ENABLE_NATS=true`.

### 5.3 Frontend obligatoria

- `VITE_API_URL` — base URL del backend en Render.

### 5.4 Frontend opcional

- `VITE_WS_URL` — si se omite, se deriva desde `VITE_API_URL`.

### 5.5 Solo desarrollo local

- `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_HOST`, `DB_PORT`.
- `SIGA_DB_HOST`, `SIGA_DB_PORT`.
- `POSTGRES_HOST_PORT`, `FRONTEND_PORT`.

No mostrar valores secretos en documentación, logs, respuestas HTTP ni archivos del repositorio.

## 6. Base de datos

- El backend usa `DATABASE_URL` como fuente principal.
- La URL se convierte al driver asíncrono `postgresql+asyncpg://`.
- `sslmode` se elimina de la query antes de pasarla a asyncpg para evitar `connect() got an unexpected keyword argument 'sslmode'`.
- La decisión SSL se lee de la URL original:
  - `sslmode=disable` → SSL desactivado;
  - `require`, `verify-ca`, `verify-full` → SSL activado;
  - sin `sslmode` → SSL activado solo en producción con host externo.
- Para URLs construidas desde variables `DB_*`, se puede usar `DB_SSLMODE`.
- Alembic usa la misma base pero con psycopg3 mediante `build_sync_database_url()`.
- `alembic.ini` no contiene URL embebida.
- Revisión actual confirmada: `b1c2d3e4f5a6 (head)`.
- Smoke con base vacía creó 23 tablas.

### 6.1 Migraciones

- Ejecutar `alembic upgrade head` en el arranque salvo que `SKIP_MIGRATIONS=true`.
- Mantener `SKIP_MIGRATIONS=false` en el primer despliegue.
- Con base vacía y `SKIP_MIGRATIONS=true`, `/core/status` falló porque no existía `core_modules`.
- Una vez migrada la base, `SKIP_MIGRATIONS=true` puede usarse como optimización si se confirma que el esquema ya existe.

### 6.2 Importación del dump

- Archivo: `dump_siga_suiza_2026_20261021.sql`.
- No importarlo automáticamente en el arranque.
- Importarlo manualmente con `psql` usando la URL interna o externa que entregue Render.
- El dump viene de PostgreSQL 18; si el destino es PostgreSQL 16, quitar:
  - `\restrict`
  - `\unrestrict`
  - `SET transaction_timeout = 0;`
- No ejecutar migraciones destructivas ni borrar tablas existentes.
- No agregar el dump al repositorio si contiene datos sensibles.

## 7. CORS

- El Core usa `FRONTEND_URL` y `CORS_ORIGINS`.
- En producción se usa la lista configurada, no un regex abierto.
- En desarrollo se conservan orígenes `localhost` habituales.
- La autenticación usa Bearer token en `localStorage`, no cookies; por eso `allow_credentials=False`.
- Revisar errores CORS y mixed content después del despliegue.

## 8. Microservicios internos

`start_railway.sh` exporta las URLs internas y levanta estos procesos:

| Puerto | Módulo |
|---:|---|
| 8001 | `mod-usuarios` |
| 8002 | `mod-planes-estudio` |
| 8005 | `mod-programas-estudio` |
| 8006 | `mod-gestion-academica` |
| 8007 | `mod-auditoria` |
| 8008 | `mod-evaluacion` |
| 8009 | `mod-admision` |

No exponer estos puertos en Render. El único puerto público del backend es `$PORT`.

## 9. NATS

- Con `ENABLE_NATS=false`, el Core Event Bus, los Outbox Workers y el Event Listener de Auditoría quedan desactivados.
- HTTP, login, health checks y módulos internos funcionan sin NATS.
- Para habilitarlo:
  1. Crear un NATS privado accesible solo desde Render.
  2. Configurar `ENABLE_NATS=true`.
  3. Configurar `NATS_URL` con el host interno y puerto `4222`.
- El código usa pub/sub simple; no configurar JetStream.

## 10. Archivos clave del backend

- `Dockerfile`: imagen de producción del Web Service.
- `.dockerignore`: excluye `.env`, Excel, dumps, logs y documentación del contexto de build.
- `siga_backend/start_railway.sh`: arranque Render/Railway del Core + módulos.
- `siga_backend/app/core/db_url.py`: construcción segura de URLs y SSL.
- `siga_backend/app/core/config.py`: variables, CORS y guards de producción.
- `siga_backend/app/main.py`: FastAPI, CORS, health, status, gateway y WebSocket.
- `siga_backend/alembic/env.py`: migraciones con psycopg3.
- `siga_backend/db_scripts/000_outbox_events.sql`: pre-creación compartida de outbox.
- `siga_backend/modules/*/database.py`: motores de cada módulo usando el helper central.

Docker Compose sigue siendo para desarrollo local y no debe eliminarse.

## 11. Archivos clave del frontend

- `siga_frontend/src/core/api/client.jsx`: `API_BASE` y `WS_BASE`.
- `siga_frontend/src/modules/finances/lib/tesoreriaApi.js`: base pública de tesorería.
- `siga_frontend/public/boleta.html`: usa el placeholder `__SIGA_API_BASE__`.
- `siga_frontend/vite.config.js`: inyecta `VITE_API_URL` en `dist/boleta.html` durante el build.
- `siga_frontend/dist`: output publicado en Render.

No debe quedar `http://localhost:8000` fijo en producción.

## 12. Verificación local

Reconstruir el stack:

```powershell
docker compose up -d --build
```

Comprobar:

```powershell
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/core/status
curl.exe http://localhost:8000/docs
curl.exe http://localhost:8000/openapi.json
```

También deben responder `200`:

```text
http://localhost:5173/
http://localhost:8001/health
http://localhost:8002/health
http://localhost:8005/health
http://localhost:8006/health
http://localhost:8007/health
http://localhost:8008/health
http://localhost:8009/health
```

Estado verificado localmente: todos esos endpoints respondieron `200` y `/core/status` reportó `7/7` módulos sanos en entorno `development`.

## 13. Verificación en Render

Definir en la sesión local una variable temporal con la URL real del backend, sin guardarla en archivos:

```powershell
$BACKEND_URL = "<URL_PUBLICA_DEL_BACKEND_RENDER>"
```

Comprobar:

```powershell
curl.exe "$BACKEND_URL/health"
curl.exe "$BACKEND_URL/core/status"
curl.exe "$BACKEND_URL/openapi.json"
```

Resultado esperado:

- `/health` → `200`.
- `/core/status` → `200` con `7/7` módulos healthy.
- `/docs` → `404` en producción.
- `/openapi.json` → `200`.
- Login y navegación principal sin errores CORS.
- Boleta pública usando `VITE_API_URL`.

## 14. Estado de pruebas

### Pasaron

- `docker build -f Dockerfile -t siga-render-test:local .`
- `python -m compileall -q app modules alembic` dentro de la imagen.
- Smoke de Render con PostgreSQL temporal y credenciales dummy:
  - migraciones hasta `b1c2d3e4f5a6 (head)`;
  - 23 tablas creadas;
  - `/health` `200`;
  - `/core/status` `200` con `7/7` módulos;
  - `/docs` `404`;
  - `/openapi.json` `200`;
  - puertos internos `200`.
- Rebuild local de Docker Compose y todos los curls indicados en la sección 12.
- Build frontend con Node 22.
- `dist/boleta.html` contiene la API inyectada y ya no contiene el placeholder.
- Una ejecución de la suite frontend pasó `70/70`.
- `src/test/docente_evaluation.test.jsx` aislado pasó `14/14`.

### No estables o fallaron

- Ejecutar tests frontend desde Windows bind mount produjo `Failed to start forks worker ... Timeout waiting for worker to respond`.
- Ejecutar en filesystem interno con `--pool=threads --maxWorkers=2` pasó una vez `70/70`, pero otra vez falló `10/70` por timeouts.
- `--isolate=false` produjo fallos artificiales por DOM compartido; no es configuración válida.
- `--testTimeout=15000 --maxWorkers=2`: `7 failed / 63 passed`.
- `--maxWorkers=1 --testTimeout=15000`: entre `1 failed / 69 passed` y `2 failed / 68 passed`.

Conclusión: el build de producción funciona, pero la suite frontend no es estable. No se cambió lógica de negocio ni tests para forzar resultados.

## 15. Errores comunes

- `connect() got an unexpected keyword argument 'sslmode'`: usar `app/core/db_url.py`; no pasar `sslmode` en `connect_args`.
- `password authentication failed`: asegurar que la URL real conserva el password al construir el engine.
- `relation "core_modules" does not exist`: ejecutar migraciones; no usar `SKIP_MIGRATIONS=true` con base vacía.
- `No module named psycopg2`: Alembic usa psycopg3; no usar URLs `+psycopg2`.
- Frontend sin conexión: revisar `VITE_API_URL`, CORS y HTTPS.
- HTTP 405: revisar método y ruta llamada; no apuntar al dominio estático.
- Módulo 8006 sin responder: revisar `SIGA_MODULE_GESTION_ACADEMICA_URL` y health checks internos.
- Problemas de puerto: Render asigna `$PORT`; no hardcodear `8000` en producción.

## 16. Procedimiento de despliegue

1. Revisar cambios y decidir si se estabilizan los tests frontend.
2. Hacer commit de los cambios.
3. Hacer push a GitHub.
4. Crear PostgreSQL en Render.
5. Crear el Backend Web Service Docker desde el `Dockerfile` raíz.
6. Configurar las variables backend obligatorias y opcionales.
7. Configurar health check `/health`.
8. Crear el Frontend Static Site desde `siga_frontend`.
9. Configurar `VITE_API_URL` y la rewrite SPA.
10. Verificar `/health`, `/core/status`, `/openapi.json` y login.
11. Importar el dump manualmente si se requieren datos reales.
12. Confirmar que `/core/status` muestre `7/7` módulos sanos.

No hacer commit ni push automáticamente; esas acciones las ejecuta el usuario.
