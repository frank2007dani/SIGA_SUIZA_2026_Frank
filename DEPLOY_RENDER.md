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
- `start_railway.sh` escucha en `0.0.0.0:$PORT` y, con `SIGA_SINGLE_PROCESS=true`, carga los 7 módulos dentro del mismo proceso Uvicorn.
- No se lanzan los Uvicorn internos de los puertos 8001/8002/8005/8006/8007/8008/8009 en producción.
- El Gateway es el único punto HTTP público: `POST /auth/login` está registrado directamente en `app/main.py`; el proxy `/api/{modulo}/{ruta}` es solo para módulos.
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
- En producción externa se usa un `ssl.SSLContext` cifrado con `check_hostname=False` y `verify_mode=ssl.CERT_NONE`, porque el hostname interno de Render no coincide con el certificado público. No es SSL desactivado.
- `app/core/db_url.py` centraliza URL, `connect_args`, pool y cierre de motores. La URL construida con `DB_*` usa `env_database_url()`.
- Pools por defecto en producción: `DB_POOL_SIZE=2`, `DB_MAX_OVERFLOW=3`, `DB_POOL_TIMEOUT=10`, `DB_POOL_RECYCLE=180`, `pool_pre_ping=True`. En tests se usa `NullPool`.
- `dispose_all_engines()` se ejecuta en el shutdown del Core. Las dependencias de sesión hacen `rollback()` antes de `close()`.
- Alembic usa la misma URL pero con driver sincrónico `psycopg` (psycopg3).

## 6. Variables de entorno

Obligatorias en Render backend:

- `DATABASE_URL` — Render la genera desde PostgreSQL.
- `DB_SSLMODE=require`.
- `SECRET_KEY` — generar un valor seguro en Render.
- `PORT` — Render lo asigna automáticamente.
- `ENVIRONMENT=production`.
- `DEBUG=false`.
- `FRONTEND_URL=https://siga-frontend-pkpc.onrender.com` o `CORS_ORIGINS` con ese mismo origen.
- `ENABLE_NATS=false`.

Recomendadas en Render backend:

- `SKIP_MIGRATIONS=true` — Alembic no se ejecuta en el arranque.
- `SIGA_SINGLE_PROCESS=true` — evita múltiples Uvicorn en el plan Free.
- `DB_POOL_SIZE=2`, `DB_MAX_OVERFLOW=3`, `DB_POOL_TIMEOUT=10`, `DB_POOL_RECYCLE=180`.

Opcionales:

- `NATS_URL` — solo si `ENABLE_NATS=true`.
- `VITE_API_URL`, `VITE_WS_URL` solo en el build del frontend.

Solo desarrollo local:

- `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_HOST`, `DB_PORT`, `SIGA_DB_HOST`, `SIGA_DB_PORT`.
- `POSTGRES_HOST_PORT`, `FRONTEND_PORT`.

Plantilla: `.env.example`. No subir valores secretos.

## 7. CORS

- El Core usa `FRONTEND_URL` y `CORS_ORIGINS`, sin regex abierta ni `*`.
- En Render configurar `FRONTEND_URL=https://siga-frontend-pkpc.onrender.com`.
- En desarrollo se mantienen `localhost:5173` y puertos locales habituales.
- La autenticación es Bearer en `localStorage`, no cookies; por eso `allow_credentials=False`.
- Si el navegador reporta `Disallowed CORS origin`, falta esa variable en el backend y se requiere restart/redeploy.

## 8. Health check

- `GET /health` responde `{"status": "healthy", ...}` sin secretos.
- Configurar `/health` en el Web Service de Render.
- `/core/status` muestra cuántos módulos internos están healthy.

## 9. Microservicios

- No crear 7 Web Services públicos.
- Con `SIGA_SINGLE_PROCESS=true`, los módulos se cargan en proceso con `inprocess_modules.install()`; no se escuchan puertos internos.
- Los antiguos puertos 8001/8002/8005/8006/8007/8008/8009 solo existen en la rama multi-proceso de desarrollo.
- El único puerto público del backend es `$PORT`.
- `app/core/gateway/http_proxy.py` usa transporte ASGI interno y propaga `X-Request-ID` desde `request.state`.

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

- En Web Service: `DATABASE_URL`, `DB_SSLMODE=require`, `SECRET_KEY`, `PORT`, `ENVIRONMENT=production`, `DEBUG=false`, `FRONTEND_URL=https://siga-frontend-pkpc.onrender.com`, `CORS_ORIGINS=https://siga-frontend-pkpc.onrender.com`, `ENABLE_NATS=false`, `SKIP_MIGRATIONS=true`, `SIGA_SINGLE_PROCESS=true`.
- En Static Site: `VITE_API_URL=https://siga-backend-pog5.onrender.com`; no configurar `VITE_WS_URL` salvo que exista un backend WebSocket real.
- `VITE_API_URL` debe ser absoluta, HTTPS y sin barra final. El build falla si falta o es relativa.
- Cambiar `VITE_*` requiere rebuild/redeploy; el asset actual desplegado sigue siendo `/assets/index-D9kB07sK.js` y no contiene el código corregido.
- Nunca pegar `DATABASE_URL` ni `SECRET_KEY` en el repo ni en logs.

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
2. Hacer login; la petición debe ser `POST https://siga-backend-pog5.onrender.com/auth/login?email=...&password=...` con query params, no JSON body ni form-data.
3. Verificar que `/core/status` muestre `healthy: 7`.
4. Probar una boleta pública con `?recibo=`; depende de `VITE_API_URL`.
5. Revisar la consola del navegador por errores CORS o mixed content.

Comprobaciones HTTP equivalentes:

```powershell
curl.exe -i "https://siga-backend-pog5.onrender.com/health"
curl.exe -i "https://siga-backend-pog5.onrender.com/core/status"
curl.exe -i -X POST "https://siga-backend-pog5.onrender.com/auth/login?email=USUARIO_CODIFICADO&password=PASSWORD_CODIFICADO"
curl.exe -i -X OPTIONS "https://siga-backend-pog5.onrender.com/auth/login" -H "Origin: https://siga-frontend-pkpc.onrender.com" -H "Access-Control-Request-Method: POST"
curl.exe -i -X POST "https://siga-frontend-pkpc.onrender.com/auth/login?email=USUARIO_CODIFICADO&password=PASSWORD_CODIFICADO"
```

Resultado esperado:

- `/health` y `/core/status`: `200`.
- `POST /auth/login` en el backend: `200` con `{ access_token, token_type, user, permissions }`.
- `OPTIONS /auth/login` en el backend con el origen real: `200` con `Access-Control-Allow-Origin`.
- `POST /auth/login` en el frontend: no debe usarse; si devuelve `405` significa que el build no inyectó `VITE_API_URL`.

## 18. Errores comunes y solución

- `connect() got an unexpected keyword argument 'sslmode'`: la URL llegó con `sslmode` a asyncpg. Usar `DATABASE_URL` y el helper `app/core/db_url.py`; nunca agregar `sslmode` a `connect_args`.
- HTTP 405 en login: confirmar que sea `POST /auth/login` con query params. Si el 405 viene del dominio frontend, el bundle tiene `VITE_API_URL` vacía o es el asset antiguo; requiere rebuild con la variable.
- `Disallowed CORS origin`: configurar `FRONTEND_URL` o `CORS_ORIGINS` en el backend y reiniciar Render.
- `SSL error: unexpected EOF while reading` o `Connection reset by peer`: revisar pools, OOM/restarts y `SIGA_SINGLE_PROCESS=true`. No desactivar `DB_SSLMODE=require`.
- Frontend sin conexión: revisar `VITE_API_URL`, CORS y que la URL sea HTTPS. No usar fallback relativo en producción.
- `No module named psycopg2`: Alembic usa psycopg3; no instalar psycopg2 ni usar URLs `+psycopg2`.
- Módulo 8006 sin responder: en modo single-process no existen puertos internos; revisar `/core/status` y los errores de importación del módulo.
- Problemas de puerto: Render asigna `$PORT`; no hardcodear 8000 en producción.
- Config vieja de Railway/Vercel: se conserva como histórico; Render usa `Dockerfile` raíz y `start_railway.sh`.

## 19. Resultado de la auditoría final

- El frontend actual usa `import.meta.env.VITE_API_URL` y no tiene fallback hardcodeado en el código fuente.
- El bundle desplegado en el momento de la auditoría era viejo (`/assets/index-D9kB07sK.js`) y todavía construía la URL con `base || "https://siga-backend-pog5.onrender.com"`; por eso el diagnóstico remoto parecía contradictorio.
- El backend ya respondió `200` a `POST /auth/login` con admin; el endpoint y la contraseña no están rotos.
- `GET /auth/login` devuelve `405` con `allow: POST`; es comportamiento correcto del endpoint.
- `POST` al dominio frontend devuelve `405` porque el Static Site sirve solo la SPA; esa no es la URL de login.
- `OPTIONS` devolvió `400 Disallowed CORS origin`; se corrige con `FRONTEND_URL`/`CORS_ORIGINS`, no con `*`.
- NATS no interviene en login; `ENABLE_NATS=false` es suficiente para HTTP.
- El riesgo real de DB en Render Free era la combinación de muchos pools y posible multi-proceso/OOM, no una credencial SSL inválida.
- No se hicieron cambios de esquema, tablas, credenciales, endpoints ni lógica de negocio; solo comunicación, configuración, pools y cierre limpio.

Validaciones ejecutadas sobre el árbol corregido:

- `python -m compileall -q app modules` en `siga_backend`: OK.
- `npm run build` con `VITE_API_URL=https://siga-backend-pog5.onrender.com`: OK; el bundle contiene la URL del backend, no contiene `__SIGA_API_BASE__` ni el patrón del bundle viejo `b=y(void 0)`.
- `npm run build` sin `VITE_API_URL`: falla con `VITE_API_URL debe ser HTTPS en el build de producción de Render`.
- `npm run lint`: falla con 48 problemas preexistentes; ninguno corresponde a `client.jsx` ni `vite.config.js`.
- `python -m pytest -q` contra `siga_test`: `30 passed, 96 skipped`.
- Checks remotos actuales: `/health=200`, `/core/status=200`, `OPTIONS /auth/login` sin CORS configurado en Render=`400`, `POST /auth/login` al Static Site=`405`.
- `docker build`: bloqueado porque Docker Desktop no tiene el daemon Linux disponible en este equipo.
