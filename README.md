# SIGA - Sistema Integrado de Gestión Académica

Este es el repositorio principal del Sistema Integrado de Gestión Académica (SIGA) para el Instituto de Educación Superior Tecnológico Público (IESTP).

Toda la documentación arquitectónica, técnica y de negocio oficial se encuentra centralizada en la carpeta `docs/`.

👉 **[Ver Documentación Principal (Índice Maestro)](docs/00-INDICE.md)**

Para conocer el estado actual y los siguientes pasos, revisa el [Informe de Estado](_estado.md).

## Arrancar con Docker
Copiar `.env.example` a `.env` (la contraseña de PostgreSQL es obligatoria) y ejecutar en la raíz:

```powershell
docker compose up -d --build
```

- Frontend: http://localhost:5173
- API / docs del Core: http://localhost:8000 / http://localhost:8000/docs
- PostgreSQL: `localhost:5433` (usuario y BD definidos en `.env`)

El stack incluye PostgreSQL, NATS, Redis, Core, los 7 módulos y el frontend con hot reload.
Para usar la PostgreSQL del host, poner `SIGA_DB_HOST=host.docker.internal` en `.env`.
Para apagar: `docker compose down` (los datos quedan en el volumen `postgres_data`).

## Contribuir
Ver [CONTRIBUTING.md](CONTRIBUTING.md). Configuración local: copiar `siga_backend/.env.example` a `.env`.
