Quiero que hagas una última revisión y corrección del proyecto `SIGA_SUIZA_2026_Frank`, específicamente para dejar funcionando correctamente la comunicación:

FRONTEND (React/Vite)
↓
BACKEND (FastAPI)
↓
POSTGRESQL (Render)

Contexto actual:

- Rama de trabajo: `RENDER`
- Frontend en `siga_frontend`
- Backend en `siga_backend`
- Backend desplegado en Render:
  `https://siga-backend-pog5.onrender.com`
- Frontend desplegado en Render:
  `https://siga-frontend-pkpc.onrender.com`
- PostgreSQL está en Render.
- El backend actualmente funciona en modo de proceso único.
- `POST /auth/login` funciona directamente en el backend.
- `GET /auth/me` funciona directamente en el backend.
- El problema histórico 405 ocurre cuando el frontend intenta enviar `/auth/login` a su propio dominio en lugar del backend.
- El problema actual de CORS aparece porque el backend todavía necesita aceptar el origen real del frontend.
- NO quiero agregar NATS para solucionar esto. NATS debe permanecer desactivado (`ENABLE_NATS=false`).
- NO cambies la lógica de negocio, modelos, autenticación ni contratos de las APIs salvo que sea estrictamente necesario para solucionar la comunicación.
- NO hagas commit ni push. Yo haré el push manualmente después.

OBJETIVO PRINCIPAL

Dejar el código preparado para que, después de hacer build y desplegar en Render, ocurra exactamente esto:

1. El usuario abre:
   https://siga-frontend-pkpc.onrender.com

2. El frontend hace login contra:
   https://siga-backend-pog5.onrender.com/auth/login

3. El backend procesa:
   FastAPI → AuthService → PostgreSQL

4. El backend devuelve el JWT.

5. El frontend guarda el token y posteriormente hace:
   https://siga-backend-pog5.onrender.com/auth/me

6. Todas las rutas `/auth`, `/api`, `/core` y las demás llamadas API deben apuntar al backend mediante la URL configurada en `VITE_API_URL`.

7. El frontend NUNCA debe intentar hacer:
   https://siga-frontend-pkpc.onrender.com/auth/login

CORRECCIONES QUE DEBES VERIFICAR

A. FRONTEND

Revisa `siga_frontend/src/core/api/client.jsx` y cualquier archivo relacionado con las peticiones.

Debe existir una construcción equivalente a:

`const API_BASE = normalizeBase(import.meta.env.VITE_API_URL)`

y las peticiones deben construirse usando:

`API_BASE + endpoint`

Verifica especialmente:

- `/auth/login`
- `/auth/me`
- `/api/...`
- `/core/...`

No dejes rutas absolutas incorrectas.
No dejes URLs localhost.
No dejes URLs relativas que hagan que el navegador use el dominio del frontend.

B. VITE_API_URL

Revisa la configuración de Vite y confirma que el proyecto permite utilizar:

`VITE_API_URL=https://siga-backend-pog5.onrender.com`

Recuerda que `VITE_API_URL` se incorpora durante el BUILD, por lo que el código debe quedar preparado para que Render la utilice correctamente.

Haz una validación del build y comprueba que el bundle generado contenga:

`https://siga-backend-pog5.onrender.com`

y que NO contenga:

- `localhost`
- `127.0.0.1`
- `https://siga-frontend-pkpc.onrender.com/auth/login`

C. NGINX DEL FRONTEND

Revisa `siga_frontend/nginx.conf`.

El frontend y backend están en servicios separados de Render.

Por lo tanto:

- NO debe existir `proxy_pass http://siga-core:8000`
- NO debe depender de un hostname Docker llamado `siga-core`
- Nginx debe servir correctamente la SPA de React
- Debe existir fallback hacia `index.html`

La comunicación frontend/backend debe realizarse mediante `VITE_API_URL`, no mediante proxy interno Docker.

D. CORS DEL BACKEND

Revisa toda la configuración CORS del backend.

Debe permitir específicamente el origen:

`https://siga-frontend-pkpc.onrender.com`

Debe ser posible configurar esto mediante variables de entorno como:

`FRONTEND_URL=https://siga-frontend-pkpc.onrender.com`

o:

`CORS_ORIGINS=https://siga-frontend-pkpc.onrender.com`

Utiliza el mecanismo que ya tenga implementado el proyecto. No dupliques innecesariamente la configuración.

Asegúrate de que una petición:

OPTIONS /auth/login

desde:

Origin: https://siga-frontend-pkpc.onrender.com

no sea rechazada por CORS.

También verifica que el middleware CORS esté aplicado correctamente antes de las rutas.

E. LOGIN

Revisa exactamente cómo espera recibir los datos:

`POST /auth/login`

No cambies el contrato del backend simplemente para adaptarlo al frontend.

El frontend debe enviar la petición exactamente como el backend la espera actualmente.

Confirma:

- status 200 con credenciales válidas
- respuesta JSON
- `access_token`
- `token_type`
- información del usuario

F. TOKEN

Revisa que después del login:

- el token se guarde correctamente
- las peticiones protegidas utilicen:

`Authorization: Bearer <token>`

- `/auth/me` utilice el backend real
- no se pierda el token al recargar la aplicación

G. BACKEND Y POSTGRESQL

No cambies la arquitectura actual que ya funciona.

Mantén:

- `DATABASE_URL`
- `DB_SSLMODE=require`
- pool optimizado
- proceso único
- PostgreSQL de Render

No vuelvas a implementar los 7 microservicios como procesos Uvicorn independientes.

No agregues NATS solamente para resolver login/CORS.

H. VARIABLES DE RENDER

Al finalizar, indícame claramente cuáles variables deben estar configuradas en Render.

Para BACKEND, verifica especialmente:

`DATABASE_URL`
`SECRET_KEY`
`ENVIRONMENT=production`
`DEBUG=false`
`DB_SSLMODE=require`
`ENABLE_NATS=false`
`SKIP_MIGRATIONS=true`
`SIGA_SINGLE_PROCESS=true`
`FRONTEND_URL=https://siga-frontend-pkpc.onrender.com`

y las variables de pool que ya utiliza el proyecto.

Para FRONTEND, verifica:

`VITE_API_URL=https://siga-backend-pog5.onrender.com`

No necesito que modifiques Render directamente; solamente dime exactamente qué debo configurar allí.

I. PRUEBAS

Antes de terminar, realiza las pruebas que sean posibles localmente:

1. `npm run build`
2. Validación del bundle generado.
3. `compileall` del backend si corresponde.
4. Pruebas existentes del backend.
5. Revisar que no existan URLs localhost en producción.
6. Revisar que no existan llamadas relativas incorrectas para `/auth`, `/api` o `/core`.

También quiero que revises el código completo buscando cualquier otra llamada que todavía esté usando:

`fetch("/auth/...")`
`axios("/auth/...")`
`fetch("/api/...")`
`fetch("/core/...")`

sin pasar por el cliente/API base correspondiente.

IMPORTANTE:

No quiero que solamente me digas qué está mal.

QUIERO QUE APLIQUES LAS CORRECCIONES NECESARIAS EN LOS ARCHIVOS DEL PROYECTO.

Después:

1. Ejecuta las validaciones.
2. Muéstrame exactamente qué archivos modificaste.
3. Explica brevemente qué corregiste en cada uno.
4. Indica qué variables debo configurar manualmente en Render.
5. Indica exactamente qué pruebas debo hacer después del deploy para confirmar:

Frontend
→ Backend
→ PostgreSQL

6. NO hagas `git commit`.
7. NO hagas `git push`.

Al final dame un resumen con este formato:

ESTADO DEL CÓDIGO:
- Frontend → Backend: OK / PENDIENTE
- CORS: OK / PENDIENTE
- Login: OK / PENDIENTE
- JWT: OK / PENDIENTE
- Backend → PostgreSQL: OK / PENDIENTE
- Nginx: OK / PENDIENTE
- Build frontend: OK / PENDIENTE
- NATS: NO NECESARIO / NECESARIO

CAMBIOS REALIZADOS:
[lista de archivos y cambios]

VARIABLES QUE DEBO CONFIGURAR EN RENDER:
[lista exacta]

PRUEBAS QUE DEBO HACER EN RENDER:
[pasos exactos]

NO HAGAS COMMIT NI PUSH.