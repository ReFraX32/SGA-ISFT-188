# --------------------------------------------------------------------------
# MÓDULO: Gestión de Docentes — VISTAS
# --------------------------------------------------------------------------
# Este archivo vive en gestion/docentes/views.py, separado del resto de
# gestion/views.py. Se conecta con el sistema principal a través de
# gestion/urls.py, que importa este módulo y registra sus rutas.
# --------------------------------------------------------------------------

from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from gestion.models import Docente
from .excel_import import procesar_importacion_docentes_excel


@login_required(login_url='login:login')
@csrf_protect
def docentes_view(request):
    """Módulo de búsqueda y consulta de docentes."""
    query = request.GET.get('q', '').strip()[:100]

    docentes = Docente.objects.select_related('persona').all()

    if query:
        query_clean = query.replace('.', '').replace(' ', '').replace('-', '').replace(',', '')
        filtros_q = (
            Q(persona__nombre__icontains=query) |
            Q(persona__apellido__icontains=query) |
            Q(persona__localidad__icontains=query) |
            Q(titulo_mn__icontains=query)
        )

        if query_clean.isdigit() or any(c.isdigit() for c in query):
            filtros_q |= Q(persona__dni__icontains=query) | Q(persona__dni__icontains=query_clean)
            filtros_q |= Q(persona__cuil__icontains=query) | Q(persona__cuil__icontains=query_clean)

        docentes = docentes.filter(filtros_q).distinct()

    docentes = docentes.order_by('persona__apellido', 'persona__nombre')

    paginator = Paginator(docentes, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'gestion/docentes.html', {
        'query': query,
        'page_obj': page_obj,
        'docentes': page_obj.object_list,
        'total_resultados': paginator.count,
    })


@login_required(login_url='login:login')
@csrf_protect
def importar_docentes_view(request):
    """
    Procesa la subida de un archivo Excel (.xlsx/.xls) para importar o actualizar docentes.
    Retorna el resultado en formato JSON para visualización interactiva con reporte de errores.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensaje': 'Método no permitido. Se requiere POST.'}, status=405)

    archivo = request.FILES.get('archivo_excel')
    if not archivo:
        return JsonResponse({'success': False, 'mensaje': 'No se seleccionó ningún archivo Excel para subir.'}, status=400)

    if not (archivo.name.endswith('.xlsx') or archivo.name.endswith('.xls')):
        return JsonResponse({'success': False, 'mensaje': 'El archivo debe tener extensión .xlsx o .xls.'}, status=400)

    resultado = procesar_importacion_docentes_excel(archivo)
    return JsonResponse(resultado)
