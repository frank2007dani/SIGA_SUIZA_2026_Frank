#!/bin/sh
set -e

echo "=========================================="
echo "🚀 Iniciando SIGA Backend (Railway)"
echo "=========================================="

PORT="${PORT:-8000}"
export PORT
echo "📡 Puerto principal: $PORT"

# Valores seguros por defecto para producción; Railway puede sobreescribirlos.
: "${ENVIRONMENT:=production}"
: "${DEBUG:=False}"
: "${ENABLE_NATS:=False}"
: "${CACHE_ENABLED:=False}"
: "${MODULES_AUTO_DISCOVER:=True}"
: "${MODULES_VALIDATE_ON_START:=True}"

export ENVIRONMENT DEBUG ENABLE_NATS CACHE_ENABLED MODULES_AUTO_DISCOVER MODULES_VALIDATE_ON_START

if [ "$ENVIRONMENT" = "production" ]; then
    if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "change-me-in-production" ]; then
        echo "ERROR: SECRET_KEY debe configurarse en las variables de Railway." >&2
        exit 1
    fi
fi

if [ -n "$DATABASE_URL" ]; then
    echo "📦 DATABASE_URL detectada de Railway."

    # Se conserva la DATABASE_URL original de Railway.
    # No se agrega sslmode=require porque el backend utiliza asyncpg.
    export DATABASE_URL

    # Para las partes del backend que utilizan psycopg,
    # normalizamos el esquema de PostgreSQL.
    DB_URL=$(printf '%s' "$DATABASE_URL" | sed \
        -e 's/^postgresql+asyncpg:\/\//postgresql+psycopg:\/\//' \
        -e 's/^postgresql:\/\//postgresql+psycopg:\/\//')

    export DB_URL
else
    echo "ADVERTENCIA: DATABASE_URL no definida; se usaran las variables DB_*."
fi

cleanup() {
    echo "🛑 Deteniendo servicios internos..."
    trap - EXIT INT TERM
    kill 0 2>/dev/null || true
}

trap cleanup EXIT INT TERM

if [ "$SKIP_MIGRATIONS" != "true" ]; then
    echo "🔄 Ejecutando migraciones de base de datos..."

    attempt=1

    until alembic -c alembic.ini upgrade head; do
        if [ "$attempt" -ge 5 ]; then
            echo "ERROR: las migraciones fallaron tras $attempt intentos; abortando arranque." >&2
            exit 1
        fi

        attempt=$((attempt + 1))
        echo "Reintentando migraciones en 5s ($attempt/5)..."
        sleep 5
    done
fi

export SIGA_MODULE_USUARIOS_URL="http://127.0.0.1:8001"
export SIGA_MODULE_PLANES_ESTUDIO_URL="http://127.0.0.1:8002"
export SIGA_MODULE_PROGRAMAS_ESTUDIO_URL="http://127.0.0.1:8005"
export SIGA_MODULE_GESTION_ACADEMICA_URL="http://127.0.0.1:8006"
export SIGA_MODULE_AUDITORIA_URL="http://127.0.0.1:8007"
export SIGA_MODULE_EVALUACION_URL="http://127.0.0.1:8008"
export SIGA_MODULE_ADMISION_URL="http://127.0.0.1:8009"

echo "⚙️ Levantando 7 microservicios internos..."

python -m uvicorn main:app --host 127.0.0.1 --port 8001 --app-dir modules/mod-usuarios &
python -m uvicorn main:app --host 127.0.0.1 --port 8002 --app-dir modules/mod-planes-estudio &
python -m uvicorn main:app --host 127.0.0.1 --port 8005 --app-dir modules/mod-programas-estudio &
python -m uvicorn main:app --host 127.0.0.1 --port 8006 --app-dir modules/mod-gestion-academica &
python -m uvicorn main:app --host 127.0.0.1 --port 8007 --app-dir modules/mod-auditoria &
python -m uvicorn main:app --host 127.0.0.1 --port 8008 --app-dir modules/mod-evaluacion &
python -m uvicorn main:app --host 127.0.0.1 --port 8009 --app-dir modules/mod-admision &

echo "Esperando health checks de microservicios..."

python - <<'PY'
import time
import urllib.request

PORTS = [8001, 8002, 8005, 8006, 8007, 8008, 8009]
deadline = time.time() + 90

while True:
    pending = []

    for port in PORTS:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health",
                timeout=2
            ) as response:
                if response.status != 200:
                    pending.append(port)

        except Exception:
            pending.append(port)

    if not pending:
        print("Microservicios internos listos")
        break

    if time.time() >= deadline:
        raise SystemExit(
            f"ERROR: microservicios sin responder: {pending}"
        )

    time.sleep(2)
PY

echo "🌐 Iniciando Core Gateway en 0.0.0.0:$PORT..."

python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" &

core_pid=$!

wait "$core_pid"