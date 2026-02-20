#!/bin/bash
set -e

echo "=== Serpent RAG — Starting ==="

# Ensure Python can find the app module
export PYTHONPATH="/app:${PYTHONPATH}"

# Run Alembic migrations only for API server (not Celery worker)
if [[ "$1" == "uvicorn" ]]; then
    echo "Running database migrations..."
    alembic upgrade head
    echo "Migrations complete."
fi

# Start the application
exec "$@"
