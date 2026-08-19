# Sistema de Gestión Académica — ISFT N° 188
Plataforma institucional para la consulta centralizada de alumnos, expedientes académicos y trayectorias curriculares del **Instituto Superior de Formación Técnica N° 188** (General Rodríguez, Pcia. de Buenos Aires).

## Características Principales
- **Arquitectura Normalizada (DER 3NF):** Cumplimiento estricto del estándar de normalización relacional en Tercera Forma Normal.
- **Búsqueda Predictiva Multicriterio:** Por DNI, CUIL, Nombre, Apellido, Localidad o Legajo.
- **Filtros Combinados:** Carrera, Año de Cursada (1°, 2°, 3°), Identidad de Género (`M`, `F`, `O`, `N`) y Localidad.
- **Cálculo Dinámico de Edad:** Computada en tiempo de ejecución sin persistencia redundante.
- **Expediente Digital & Constancias Oficiales:** Vista modal detallada e impresión en formato institucional A4.
- **Cobertura de Pruebas Unitarias:** 100% de pruebas aprobadas bajo Django Test Runner.

## Despliegue Rápido con Docker
```bash
docker-compose up -d --build
```

## Ejecución Local (Desarrollo)
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

## Ejecución de Tests
```bash
python manage.py test gestion
```
