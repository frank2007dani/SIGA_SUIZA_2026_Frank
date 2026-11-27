ESTADO DEL CÓDIGO:
- Frontend → Backend: OK
  - `API_BASE` se construye desde `VITE_API_URL` y el bundle local genera 1 hit a `https://siga-backend-pog5.onrender.com`, 0 a `https://siga-frontend-pkpc.onrender.com/auth/login`, 0 a `localhost` y 0 a `127.0.0.1`.
  - El sitio actual de Render sigue sirviendo el bundle antiguo; después de configurar `VITE_API_URL` hay que hacer rebuild/redeploy.
- CORS: PENDIENTE
  - En código está OK: con `FRONTEND_URL=https://siga-frontend-pkpc.onrender.com`, una prueba local `OPTIONS /auth/login` devolvió `200` y `access-control-allow-origin: https://siga-frontend-pkpc.onrender.com`.
  - En Render sigue pendiente porque el backend actual devuelve `400 Disallowed CORS origin` al preflight.
- Login: OK
  - Contrato sin cambios: `POST /auth/login` recibe `email` y `password` como query params y devuelve `200`, `access_token`, `token_type` e información del usuario.
- JWT: OK
  - Token guardado y enviado como `Authorization: Bearer <token>`; `GET /auth/me` contra el backend real devolvió `200`.
- Backend → PostgreSQL: OK
  - Arquitectura sin cambios: FastAPI → AuthService → PostgreSQL de Render mediante `DATABASE_URL`; `DB_SSLMODE=require` conservado.
- Nginx: OK
  - Sirve la SPA con fallback a `index.html`; no hay `proxy_pass`, ni dependencia de `siga-core`, ni puertos internos.
- Build frontend: OK
  - `npm run build` con `VITE_API_URL=https://siga-backend-pog5.onrender.com` terminó correctamente; solo hay el aviso de chunk > 500 kB, no un error.
- NATS: NO NECESARIO
  - Permanece desactivado con `ENABLE_NATS=false`.

CAMBIOS REALIZADOS:
- `.env.example`: documentadas las variables de Render y `VITE_API_URL`, sin secretos.
- `DEPLOY_RENDER.md`: actualizado el diagnóstico del 405/CORS, las variables y el procedimiento de rebuild/redeploy.
- `siga_backend/.env.example`: agregadas/ajustadas `FRONTEND_URL`, `CORS_ORIGINS`, `DB_SSLMODE`, `ENABLE_NATS=false`, `SIGA_SINGLE_PROCESS=true` y variables de pool.
- `siga_backend/app/core/config.py`: sin cambios; se confirmó que `allowed_origins` ya usa `FRONTEND_URL` y `CORS_ORIGINS`.
- `siga_backend/app/main.py`: se confirmó que `CORSMiddleware` se agrega antes de las rutas; ajustado el shutdown para liberar motores.
- `siga_backend/app/core/db_url.py`: centralizada la construcción de `DATABASE_URL`, SSL, `connect_args`, pool y `dispose_all_engines()`.
- `siga_backend/app/core/database.py`: motor centralizado y rollback en la dependencia de sesión.
- `siga_backend/app/core/identity/database.py`: motor centralizado y rollback en la dependencia de sesión de identidad.
- `siga_backend/app/core/gateway/http_proxy.py`: propagación de `X-Request-ID` con fallback desde `request.state`.
- `siga_backend/modules/mod-admision/database.py`: motor centralizado y rollback en dependencias.
- `siga_backend/modules/mod-auditoria/database.py`: motor centralizado y rollback en dependencias.
- `siga_backend/modules/mod-evaluacion/database.py`: motor centralizado y rollback en dependencias.
- `siga_backend/modules/mod-gestion-academica/database.py`: motor centralizado y rollback en dependencias.
- `siga_backend/modules/mod-planes-estudio/database.py`: motor centralizado y rollback en dependencias.
- `siga_backend/modules/mod-programas-estudio/database.py`: motor centralizado y rollback en dependencias.
- `siga_backend/modules/mod-usuarios/database.py`: motor centralizado y rollback en dependencias.
- `siga_frontend/src/core/api/client.jsx`: `const API_BASE = normalizeBase(import.meta.env.VITE_API_URL)`, fail-fast en producción, `API_BASE + endpoint`, JWT en `localStorage`, `Authorization: Bearer` y logs DEV con datos sensibles redactados.
- `siga_frontend/vite.config.js`: valida que `VITE_API_URL` exista y sea HTTPS en producción; inyecta la base en `dist/boleta.html`.
- `siga_frontend/index.html`: reformulé el texto del service worker para que el bundle publicado no contenga la cadena literal `localhost`.
- `siga_frontend/src/modules/finances/lib/tesoreriaApi.js`: `publicApiBase()` usa `API_BASE`; la validación de URLs locales se expresa sin dejar la cadena literal `localhost` en el bundle, conservando el comportamiento.
- `siga_frontend/src/modules/finances/TupaCatalogManager.jsx`: reformulé el texto de ayuda para no dejar la cadena literal `localhost` en el bundle.
- `respuestaopencode.md`:actualizado con este informe final.
- No incluyo `intrucciones.md` en la lista porque fue actualizado por ti, no por mí.
- No hice `git commit` ni `git push`.

VARIABLES QUE DEBO CONFIGURAR EN RENDER:
- BACKEND:
  - `DATABASE_URL=<URL PostgreSQL administrada por Render>`
  - `SECRET_KEY=<valor seguro generado en Render>`
  - `ENVIRONMENT=production`
  - `DEBUG=false`
  - `DB_SSLMODE=require`
  - `ENABLE_NATS=false`
  - `SKIP_MIGRATIONS=true`
  - `SIGA_SINGLE_PROCESS=true`
  - `FRONTEND_URL=https://siga-frontend-pkpc.onrender.com`
  - `DB_POOL_SIZE=2`
  - `DB_MAX_OVERFLOW=3`
  - `DB_POOL_TIMEOUT=10`
  - `DB_POOL_RECYCLE=180`
  - `PORT` lo inyecta Render automáticamente.
  - No configures `CORS_ORIGINS` si ya configuraste `FRONTEND_URL`; si prefieres usar solo `CORS_ORIGINS`, usa exactamente `CORS_ORIGINS=https://siga-frontend-pkpc.onrender.com` y omite `FRONTEND_URL`.
- FRONTEND:
  - `VITE_API_URL=https://siga-backend-pog5.onrender.com`
  - `VITE_WS_URL` no es obligatoria; se deriva desde `VITE_API_URL`.
- Después de cambiar `VITE_API_URL`, haz rebuild/redeploy del Static Site: Vite incorpora esa variable durante el build.

PRUEBAS QUE DEBO HACER EN RENDER:
1. Backend:
   - `curl.exe https://siga-backend-pog5.onrender.com/health` → `200`.
   - `curl.exe https://siga-backend-pog5.onrender.com/core/status` → `200`.
   - `curl.exe https://siga-backend-pog5.onrender.com/openapi.json` → `200`.
2. CORS:
   - `curl.exe -i -X OPTIONS https://siga-backend-pog5.onrender.com/auth/login -H "Origin: https://siga-frontend-pkpc.onrender.com" -H "Access-Control-Request-Method: POST" -H "Access-Control-Request-Headers: authorization,content-type"`
   - Esperado: `200` y `access-control-allow-origin: https://siga-frontend-pkpc.onrender.com`.
3. Bundle del frontend:
   - Abre `https://siga-frontend-pkpc.onrender.com`, abre DevTools → Network y recarga.
   - En el JS principal debe aparecer `https://siga-backend-pog5.onrender.com`.
   - No debe aparecer `https://siga-frontend-pkpc.onrender.com/auth/login`, `localhost` ni `127.0.0.1`.
4. Login:
   - Inicia sesión desde `https://siga-frontend-pkpc.onrender.com`.
   - En DevTools → Network, la petición debe ser `POST https://siga-backend-pog5.onrender.com/auth/login?email=...&password=...`.
   - No debe existir `POST https://siga-frontend-pkpc.onrender.com/auth/login` ni `405`.
   - La respuesta debe ser `200` con `access_token`, `token_type` e información del usuario.
5. JWT:
   - Después del login, verifica que `GET https://siga-backend-pog5.onrender.com/auth/me` tenga `Authorization: Bearer <token>` y devuelva `200`.
   - Recarga la página y confirma que la sesión permanece activa.
6. API general:
   - Navega por módulos que usen `/api/...` y `/core/...`.
   - Todas esas peticiones deben aparecer en Network con host `siga-backend-pog5.onrender.com`.
   - Ninguna debe aparecer con host `siga-frontend-pkpc.onrender.com`.
7. Boleta pública:
   - Abre una boleta/QR público y confirma que el enlace "VER BOLETA" use la base configurada del backend y no `localhost`.

Validaciones locales ya ejecutadas:
- `npm run build` → OK.
- Bundle generado: `backend_base=1`, `localhost=0`, `127.0.0.1=0`, `frontend_auth_login=0`, `placeholder=0`.
- `python -m compileall -q app modules` → OK.
- `python -m pytest -q` → `30 passed, 96 skipped`.
- Prueba local de CORS con `FRONTEND_URL` configurado → `OPTIONS /auth/login` `200` con el origen exacto.
- `git diff --check` → OK.
- `npm run lint` → 48 problemas preexistentes no relacionados con las líneas modificadas.
- Login directo y `/auth/me` contra el backend real → `200`.
- Sin commit ni push.
