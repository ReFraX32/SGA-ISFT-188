from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    path('alumno/', views.portal_alumno_view, name='alumno'),
    path('docente/', views.portal_docente_view, name='docente'),
]
