# Despliegue en Render

Guía práctica para dejar `SIGA_SUIZA_2026` funcionando en Render. No incluye secretos ni URLs inventadas: los valores finales se colocan en el panel de Render.

## 1. Arquitectura

- GitHub es la fuente del código.
- Frontend React/Vite se publica como **Render Static Site**.
- Backend FastAPI se publica como **Render Web Service** usando Docker.
- PostgreSQL es administrado por Render (`DATABASE_URL`).
- pgAdmin es solo una herramienta de administración; no aloja la base.
- El contenedor del backend incluye el Core y los 7 módulos internos. PostgreSQL **no** corre dentro del contenedor en producción.

## 2. Frontend

- Directorio de build: `siga_frontend`.
- Build command: `npm ci && npm run build`.
- Publish directory: `siga_frontend/dist`.
- Variables de build: `VITE_API_URL` y `VITE_WS_URL` (opcional).
- `VITE_API_URL` debe apuntar a la URL real del backend de Render, nunca escrita en el código.
- En `vite.config.js` se inyecta automáticamente esa base en `dist/boleta.html` durante el build.
- Agregar en Render la rewrite de SPA: `/*` → `/index.html` con status `200`. Los archivos reales (`/boleta.html`, `/carreras/*`, `/assets/*`) se sirven antes de la rewrite.

## 3. Backend

- Entrypoint real: `siga_backend/app/main.py` (`app = FastAPI(...)`).
- Comando de Render: `sh ./start_railway.sh` (ya es el `CMD` del `Dockerfile` raíz).
- `start_railway.sh` escucha en `0.0.0.0:$PORT`, levanta los módulos en `127.0.0.1`, espera sus `/health` y luego inicia el Core.
- No se usa `--reload` cuando `ENVIRONMENT=production`.
- Health check de Render: `/health`.

## 4. Docker

- `Dockerfile` raíz: imagen de producción del backend.
- `siga_backend/Dockerfile`: imagen usada por Docker Compose para desarrollo.
- Root `.dockerignore` evita subir `.env`, Excel, dumps SQL, logs y documentación al contexto de build.
- Docker Compose sigue siendo desarrollo local; no se elimina.

## 5. PostgreSQL

- Render crea el servicio administrado y entrega `DATABASE_URL`.
- El backend convierte esa URL a `postgresql+asyncpg://` y quita `sslmode` de la query para evitar el error `connect() got an unexpected keyword argument 'sslmode'`.
- La decisión SSL se lee de la URL original: `sslmode=disable` desactiva SSL; `require`/`verify-ca`/`verify-full` lo activa; si no hay `sslmode`, se activa solo en producción con host externo.
- SSL se pasa a asyncpg mediante `connect_args={"ssl": True|False}` cuando corresponde.
- Para URL construida con `DB_*` en vez de `DATABASE_URL`, se puede usar `DB_SSLMODE`.
- Alembic usa la misma URL pero con driver sincrónico `psycopg` (psycopg3).

## 6. Variables de entorno

Obligatorias en Render backend:

- `DATABASE_URL` — Render la genera desde PostgreSQL.
- `SECRET_KEY` — generar un valor seguro en Render.
- `PORT` — Render lo asigna automáticamente.
- `ENVIRONMENT=production`.
- `DEBUG=false`.
- `FRONTEND_URL` o `CORS_ORIGINS` con el origen real del frontend.

Opcionales:

- `ENABLE_NATS`, `NATS_URL`, `SKIP_MIGRATIONS`.
- `PROGRAMAS_MODULE_URL`, `PLANES_MODULE_URL`.
- `VITE_API_URL`, `VITE_WS_URL` solo en el build del frontend.

Solo desarrollo local:

- `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_HOST`, `DB_PORT`, `SIGA_DB_HOST`, `SIGA_DB_PORT`.
- `POSTGRES_HOST_PORT`, `FRONTEND_PORT`.

Plantilla: `.env.example`. No subir valores secretos.

## 7. CORS

- El Core usa `FRONTEND_URL` y `CORS_ORIGINS`, sin regex abierta.
- En desarrollo se mantienen `localhost:5173` y puertos locales habituales.
- La autenticación es Bearer en `localStorage`, no cookies; por eso `allow_credentials=False`.

## 8. Health check

- `GET /health` responde `{"status": "healthy", ...}` sin secretos.
- Configurar `/health` en el Web Service de Render.
- `/core/status` muestra cuántos módulos internos están healthy.

## 9. Microservicios

- No crear 7 Web Services públicos.
- Los módulos corren dentro del mismo contenedor en `127.0.0.1`:
  - 8001 usuarios, 8002 planes, 8005 programas, 8006 gestión académica, 8007 auditoría, 8008 evaluación, 8009 admisión.
- El único puerto público del backend es `$PORT`.
- Las URLs internas se sobreescriben con `SIGA_MODULE_*_URL` en `start_railway.sh`.

## 10. NATS

- `ENABLE_NATS=false` desactiva Core Event Bus, Outbox Workers y el listener de auditoría.
- Es suficiente para que el sistema HTTP funcione.
- Para auditoría en tiempo real y entrega real de eventos, desplegar un servicio NATS privado y configurar `ENABLE_NATS=true` con `NATS_URL`.
- No usar JetStream: el código actual usa pub/sub simple.

## 11. Cómo ejecutar localmente

```powershell
docker compose up -d --build
```

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- PostgreSQL local: `localhost:5433`
- pgAdmin se conecta a `localhost:5433`; no aloja la BD.

## 12. Cómo probar el backend

```powershell
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/core/status
```

En Render, reemplazar `localhost:8000` por la URL real del servicio.

## 13. Cómo desplegar en Render

1. Crear PostgreSQL en Render y copiar su `DATABASE_URL`.
2. Crear Web Service Docker desde el repo, con `Dockerfile` raíz.
3. Configurar variables del apartado 6 y health check `/health`.
4. Crear Static Site con root `siga_frontend`, build `npm ci && npm run build` y publish `siga_frontend/dist`.
5. Configurar `VITE_API_URL` con la URL del backend y agregar la rewrite SPA.
6. Verificar `/health` y `/core/status`.

No se creó `render.yaml`: la URL final del frontend y la decisión de NATS se definen en el panel de Render.

## 14. Cómo configurar las variables de Render

- En Web Service: `DATABASE_URL`, `SECRET_KEY`, `PORT`, `ENVIRONMENT`, `DEBUG`, `FRONTEND_URL`, `CORS_ORIGINS`, `ENABLE_NATS`, `NATS_URL`.
- En Static Site: `VITE_API_URL`, `VITE_WS_URL`.
- Cambiar `VITE_*` requiere rebuild/redeploy.

## 15. Cómo conectar PostgreSQL

- El backend usa solo `DATABASE_URL`; no necesita `DB_HOST` en producción.
- pgAdmin: servidor nuevo con host/puerto/usuario/contraseña dados por Render o por Docker local.
- No pegar la `DATABASE_URL` real en archivos del repo.

## 16. Cómo importar posteriormente el dump

- Archivo disponible: `dump_siga_suiza_2026_20261021.sql`.
- No importarlo automáticamente en el arranque.
- Importarlo manualmente con `psql` usando la URL de Render, después de creada la BD.
- El dump viene de PostgreSQL 18; si el destino es 16, quitar las líneas `\restrict`, `\unrestrict` y `SET transaction_timeout = 0;`.
- No ejecutar migraciones destructivas ni borrar tablas.

## 17. Cómo comprobar que frontend y backend están conectados

1. Abrir el Static Site.
2. Hacer login; la petición debe ir a `VITE_API_URL/auth/login`.
3. Verificar que `/core/status` muestre `healthy: 7`.
4. Probar una boleta pública con `?recibo=`; depende de `VITE_API_URL`.
5. Revisar la consola del navegador por errores CORS o mixed content.

## 18. Errores comunes y solución

- `connect() got an unexpected keyword argument 'sslmode'`: la URL llegó con `sslmode` a asyncpg. Usar `DATABASE_URL` y el helper `app/core/db_url.py`; nunca agregar `sslmode` a `connect_args`.
- HTTP 405: revisar que el frontend llame al método correcto (`GET`/`POST`) y a la URL del backend, no al dominio estático.
- Frontend sin conexión: revisar `VITE_API_URL`, CORS y que la URL sea HTTPS.
- `No module named psycopg2`: Alembic usa psycopg3; no instalar psycopg2 ni usar URLs `+psycopg2`.
- Módulo 8006 sin responder: revisar `SIGA_MODULE_GESTION_ACADEMICA_URL` y los health checks internos.
- Problemas de puerto: Render asigna `$PORT`; no hardcodear 8000 en producción.
- Config vieja de Railway/Vercel: se conserva como histórico; Render usa `Dockerfile` raíz y `start_railway.sh`.
