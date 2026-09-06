from django.urls import path
from . import views
<<<<<<< HEAD
=======
from .docentes import views as docentes_views
>>>>>>> b5ebfda (Agrego mis archivos nuevos)

app_name = 'gestion'

urlpatterns = [
    path('', views.buscador_view, name='buscador'),
<<<<<<< HEAD
=======
    path('docentes/', docentes_views.docentes_view, name='docentes'),
    path('importar-docentes/', docentes_views.importar_docentes_view, name='importar_docentes'),
>>>>>>> b5ebfda (Agrego mis archivos nuevos)
    path('api/alumno/<str:dni>/', views.alumno_detalle_json, name='alumno_detalle_json'),
    path('alumno/<str:dni>/imprimir/', views.imprimir_estado_academico, name='imprimir_estado_academico'),
    path('libro-matriz/', views.descargar_libro_matriz, name='descargar_libro_matriz'),
    path('libro-matriz/<str:codigo_carrera>/', views.descargar_libro_matriz, name='descargar_libro_matriz_carrera'),
    path('plantilla-alumnos/', views.descargar_plantilla_alumnos, name='descargar_plantilla_alumnos'),
    path('importar-alumnos/', views.importar_alumnos_view, name='importar_alumnos'),
]
