# Sistema de Gestión Académica — ISFT N° 188
## Módulo 1: Buscador de Alumnos DNI y Estado Académico

Sistema web desarrollado con **Django**, **PostgreSQL** y **Docker Compose** para la gestión integral y consulta rápida del recorrido estudiantil por DNI, Nombre o Apellido.

## Estructura del Proyecto

- `gestion/`: Aplicación principal de Django (Modelos, Vistas, URLs, Plantillas).
- `sistema_alumnos/`: Configuración del proyecto (`settings.py`, `urls.py`, `wsgi.py`).
- `Dockerfile`: Construcción de imagen de producción ligera basada en Python 3.12-slim.
- `docker-compose.yml`: Orquestación de servicios y almacenamiento en volúmenes persistentes.
- `entrypoint.sh`: Automatización de arranque, migraciones y recolección estática.