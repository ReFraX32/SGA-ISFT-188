from django.urls import path
from . import views
from .docentes import views as docentes_views

app_name = 'gestion'

urlpatterns = [
    path('', views.buscador_view, name='buscador'),
    path('docentes/', docentes_views.docentes_view, name='docentes'),
    path('docentes/alta/', docentes_views.alta_docente_view, name='alta_docente'),
    path('docentes/confirmacion/', docentes_views.paso2_confirmacion_docentes, name='paso2_confirmacion_docentes'),
    path('importar-docentes/', docentes_views.importar_docentes_view, name='importar_docentes'),
    path('api/persona-datos/<str:tipo>/<str:identificador>/', views.persona_datos_json, name='persona_datos_json'),
    path('editar/<str:tipo>/<str:identificador>/', views.persona_editar_view, name='persona_editar'),
    path('eliminar/<str:tipo>/<str:identificador>/', views.persona_eliminar_view, name='persona_eliminar'),
    path('api/alumno/<str:dni>/', views.alumno_detalle_json, name='alumno_detalle_json'),
    path('api/docente/<str:dni>/', docentes_views.docente_detalle_json, name='docente_detalle_json'),
    path('alumno/<str:dni>/imprimir/', views.imprimir_estado_academico, name='imprimir_estado_academico'),
    path('docente/<str:dni>/imprimir/', docentes_views.imprimir_ficha_docente, name='imprimir_ficha_docente'),
    path('libro-matriz/', views.descargar_libro_matriz, name='descargar_libro_matriz'),
    path('libro-matriz/<str:codigo_carrera>/', views.descargar_libro_matriz, name='descargar_libro_matriz_carrera'),
    path('plantilla-alumnos/', views.descargar_plantilla_alumnos, name='descargar_plantilla_alumnos'),
    path('importar-alumnos/', views.importar_alumnos_view, name='importar_alumnos'),
]
