from django.urls import path
from . import views

app_name = 'carga_alumnos'

urlpatterns = [
    path('', views.paso1_carga, name='paso1_carga'),
    path('inicio/', views.paso1_carga, name='index'),  # Redirección directa y compatibilidad
    path('confirmacion/', views.paso2_confirmacion, name='paso2_confirmacion'),
]
