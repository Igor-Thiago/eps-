#!/bin/sh
set -e

echo "Aguardando PostgreSQL em $DB_HOST:$DB_PORT..."

until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  echo "PostgreSQL ainda nao esta pronto; aguardando 2s..."
  sleep 2
done

echo "PostgreSQL pronto. Rodando migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo "Preparando pasta de midias..."
mkdir -p /app/media/casos
mkdir -p /app/media/watch_downloads
chmod -R 777 /app/media

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

echo "Iniciando servidor Django..."
exec python manage.py runserver 0.0.0.0:8000
