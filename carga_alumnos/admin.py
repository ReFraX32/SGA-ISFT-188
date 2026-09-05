from typing import Any
from django.contrib import admin
from .models import Alumno


@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display: Any = ('dni', 'cuil', 'apellido', 'nombre', 'genero', 'localidad', 'nacionalidad', 'email', 'telefono', 'fecha_registro')
    list_filter: Any = ('genero', 'localidad', 'nacionalidad', 'fecha_registro')
    search_fields: Any = ('dni', 'cuil', 'apellido', 'nombre', 'email', 'telefono')
    ordering: Any = ('-fecha_registro',)
