#!/bin/sh
set -e

echo "=========================================="
echo "🚀 Iniciando SIGA Backend (Render/Railway)"
echo "=========================================="

PORT="${PORT:-8000}"
export PORT
echo "📡 Puerto principal: $PORT"

ENABLE_NATS="${ENABLE_NATS:-false}"
export ENABLE_NATS

SIGA_SINGLE_PROCESS="${SIGA_SINGLE_PROCESS:-true}"
export SIGA_SINGLE_PROCESS

PROGRAMAS_MODULE_URL="${PROGRAMAS_MODULE_URL:-http://127.0.0.1:8005}"
PLANES_MODULE_URL="${PLANES_MODULE_URL:-http://127.0.0.1:8002}"
export PROGRAMAS_MODULE_URL PLANES_MODULE_URL

cleanup() {
    echo "🛑 Deteniendo servicios internos..."
    kill 0 2>/dev/null || true
    exit 0
}
trap cleanup EXIT INT TERM

if [ -n "$DATABASE_URL" ] && [ -z "$DB_URL" ]; then
    echo "📦 DATABASE_URL detectada."
    export DB_URL="$DATABASE_URL"
fi

if [ "$SKIP_MIGRATIONS" != "true" ]; then
    echo "🔄 Ejecutando migraciones de base de datos..."
    alembic upgrade head || echo "⚠️ Alembic upgrade head falló o fue omitido — continuando..."
fi

export SIGA_MODULE_USUARIOS_URL="http://127.0.0.1:8001"
export SIGA_MODULE_PLANES_ESTUDIO_URL="http://127.0.0.1:8002"
export SIGA_MODULE_PROGRAMAS_ESTUDIO_URL="http://127.0.0.1:8005"
export SIGA_MODULE_GESTION_ACADEMICA_URL="http://127.0.0.1:8006"
export SIGA_MODULE_AUDITORIA_URL="http://127.0.0.1:8007"
export SIGA_MODULE_EVALUACION_URL="http://127.0.0.1:8008"
export SIGA_MODULE_ADMISION_URL="http://127.0.0.1:8009"

if [ "$SIGA_SINGLE_PROCESS" = "true" ]; then
    echo "🧩 Modo proceso único: 7 módulos dentro del Core, sin Uvicorn internos."
else
    echo "⚙️ Levantando 7 microservicios internos..."
    python -m uvicorn main:app --host 127.0.0.1 --port 8001 --app-dir modules/mod-usuarios &
    python -m uvicorn main:app --host 127.0.0.1 --port 8002 --app-dir modules/mod-planes-estudio &
    python -m uvicorn main:app --host 127.0.0.1 --port 8005 --app-dir modules/mod-programas-estudio &
    python -m uvicorn main:app --host 127.0.0.1 --port 8006 --app-dir modules/mod-gestion-academica &
    python -m uvicorn main:app --host 127.0.0.1 --port 8007 --app-dir modules/mod-auditoria &
    python -m uvicorn main:app --host 127.0.0.1 --port 8008 --app-dir modules/mod-evaluacion &
    python -m uvicorn main:app --host 127.0.0.1 --port 8009 --app-dir modules/mod-admision &

    echo "⏳ Health checks internos en segundo plano..."
    (
        ready=0
        for i in $(seq 1 60); do
            ready=0
            for port in 8001 8002 8005 8006 8007 8008 8009; do
                if curl -fsS "http://127.0.0.1:$port/health" >/dev/null 2>&1; then
                    ready=$((ready + 1))
                fi
            done
            if [ "$ready" -eq 7 ]; then
                echo "✅ 7 módulos internos listos."
                exit 0
            fi
            sleep 1
        done
        echo "⚠️ Solo $ready/7 módulos respondieron /health."
    ) &
fi

echo "🌐 Iniciando Core Gateway en 0.0.0.0:$PORT..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
