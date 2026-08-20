#!/bin/sh
set -e

# Puerto expuesto (Render/Railway inyectan la variable PORT dinamicamente)
PORT="${PORT:-8000}"

echo "Iniciando servicio para ISFT 188 en el puerto ${PORT}..."

# Intentar conectar a PostgreSQL con tiempo limite maximo (15 segundos)
if [ "$DB_ENGINE" = "postgresql" ] || [ -n "$DATABASE_URL" ] || [ -n "$DB_HOST" ]; then
    echo "Verificando conexión a la base de datos PostgreSQL..."
    MAX_RETRIES=15
    RETRY_COUNT=0
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if python -c "
import os, sys, psycopg2
try:
    url = os.environ.get('DATABASE_URL')
    if url:
        conn = psycopg2.connect(url, connect_timeout=3)
    else:
        conn = psycopg2.connect(
            dbname=os.environ.get('DB_NAME','sistema_alumnos_db'),
            user=os.environ.get('DB_USER','postgres'),
            password=os.environ.get('DB_PASSWORD','postgres'),
            host=os.environ.get('DB_HOST','localhost'),
            port=os.environ.get('DB_PORT','5432'),
            connect_timeout=3
        )
    conn.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
"; then
            echo "¡Conexión exitosa a PostgreSQL!"
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "Esperando respuesta de base de datos ($RETRY_COUNT/$MAX_RETRIES)..."
        sleep 1
    done

    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "AVISO: No se pudo conectar a PostgreSQL en el tiempo límite. Continuando arranque..."
    fi
fi

echo "Ejecutando migraciones de Django..."
python manage.py migrate --noinput

echo "Aprovisionando usuario administrador institucional (admin / mde123)..."
python manage.py crear_usuario_admin || true

echo "Recolectando archivos estáticos con WhiteNoise..."
python manage.py collectstatic --noinput

echo "Verificando e importando datos iniciales (Fixtures)..."
python manage.py loaddata initial_data || true

echo "Servidor listo. Iniciando Gunicorn en 0.0.0.0:${PORT}..."
exec gunicorn sistema_alumnos.wsgi:application --bind "0.0.0.0:${PORT}" --workers 3
