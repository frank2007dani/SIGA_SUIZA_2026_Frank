#!/bin/sh
set -e

if [ "$SKIP_MIGRATIONS" != "true" ]; then
    # Build DB URL for Alembic
    if [ -z "$DB_URL" ]; then
        if [ -n "$DATABASE_URL" ]; then
            export DB_URL="$DATABASE_URL"
        else
            export DB_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
        fi
    fi

    echo "Running database migrations..."
    if alembic upgrade head; then
        echo "Migrations applied successfully."
    else
        echo "WARNING: alembic upgrade head failed — starting without migrations."
    fi
fi

if [ "$#" -eq 0 ]; then
    PORT="${PORT:-8000}"
    if [ "$ENVIRONMENT" = "development" ] || [ "$ENVIRONMENT" = "dev" ]; then
        echo "Starting SIGA Core con Hot Reload on 0.0.0.0:$PORT..."
        exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload
    fi
    echo "Starting SIGA Core on 0.0.0.0:$PORT"
    exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
else
    echo "Starting Module with command: $@"
    exec "$@"
fi
