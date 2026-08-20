import os
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse, FileResponse

def favicon_view(request):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    favicon_path = os.path.join(base_dir, 'gestion', 'static', 'favicon.png')
    if os.path.exists(favicon_path):
        return FileResponse(open(favicon_path, 'rb'), content_type="image/png")
    return HttpResponse("", status=204)

urlpatterns = [
    path('favicon.ico', favicon_view, name='favicon'),
    path('favicon.png', favicon_view, name='favicon_png'),
    path('', include('login.urls')),
    path('', include('gestion.urls')),
]

# Habilitar ruta de administracion solo si ENABLE_ADMIN es activado explicitamente en variables de entorno
if os.environ.get('ENABLE_ADMIN', 'False').lower() in ['true', '1']:
    urlpatterns.append(path('admin/', admin.site.urls))
