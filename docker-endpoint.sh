#!/bin/sh
set -o errexit
set -o pipefail
set -o nounset

if [ -f "/app/.env.example" ] && [ ! -f "/app/.env" ]; then
    cp /app/.env.example /app/.env
fi

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

python manage.py migrate --noinput

exec python manage.py runserver 0.0.0.0:"${PORT:-8000}"
