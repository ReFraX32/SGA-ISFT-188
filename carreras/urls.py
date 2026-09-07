from django.urls import path
from . import views

app_name = 'carreras'

urlpatterns = [
    path('', views.carreras_list_view, name='carreras_list'),
    path('alta/', views.alta_carrera_view, name='alta_carrera'),
    path('alta/matriz/', views.alta_carrera_matriz_view, name='alta_carrera_matriz'),
    path('api/<str:codigo_carrera>/detalle/', views.carrera_detalle_json, name='carrera_detalle_json'),
    path('<str:codigo_carrera>/editar/', views.carrera_editar_view, name='carrera_editar'),
    path('<str:codigo_carrera>/eliminar/', views.carrera_eliminar_view, name='carrera_eliminar'),
    path('<str:codigo_carrera>/imprimir/', views.imprimir_plan_estudio, name='imprimir_plan_estudio'),
]
