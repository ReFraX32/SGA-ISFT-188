import datetime
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse, Http404
from django.db.models import Q, Avg, Count
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator
from .models import Alumno, Persona, Cursada, Carrera, PlanEstudio, Evaluacion
from .libro_matriz import generar_libro_matriz_excel

@csrf_protect
def buscador_view(request):
    if request.method == 'POST':
        query = request.POST.get('q', '').strip()
        carrera_id = request.POST.get('carrera', '').strip()
        anio_filtro = request.POST.get('anio', '').strip()
        localidad_filtro = request.POST.get('localidad', '').strip()
        orden_filtro = request.POST.get('orden', 'apellido').strip()
        page_num = request.POST.get('page', '1').strip()
        page_size_val = request.POST.get('page_size', '25').strip()
    else:
        query = request.GET.get('q', '').strip()
        carrera_id = request.GET.get('carrera', '').strip()
        anio_filtro = request.GET.get('anio', '').strip()
        localidad_filtro = request.GET.get('localidad', '').strip()
        orden_filtro = request.GET.get('orden', 'apellido').strip()
        page_num = request.GET.get('page', '1').strip()
        page_size_val = request.GET.get('page_size', '25').strip()

    if len(query) > 100:
        query = query[:100]

    try:
        page_size = int(page_size_val)
        if page_size not in [10, 25, 50, 100]:
            page_size = 25
    except (ValueError, TypeError):
        page_size = 25

    alumnos = Alumno.objects.select_related('persona').prefetch_related(
        'cursadas__comision__plan_estudio__carrera',
        'cursadas__comision__plan_estudio__materia',
        'cursadas__evaluaciones'
    ).all()

    # Búsqueda flexible por DNI (limpio/con puntos), CUIL, Nombre, Apellido, Legajo o Localidad
    if query:
        query_clean = query.replace('.', '').replace(' ', '').replace('-', '').replace(',', '')
        
        filtros_q = (
            Q(persona__nombre__icontains=query) |
            Q(persona__apellido__icontains=query) |
            Q(persona__localidad__icontains=query) |
            Q(legajo__icontains=query) |
            Q(legajo__icontains=query_clean)
        )
        
        if query_clean.isdigit() or any(c.isdigit() for c in query):
            filtros_q |= Q(persona__dni__icontains=query) | Q(persona__dni__icontains=query_clean)
            filtros_q |= (
                (Q(persona__cuil__icontains=query) | Q(persona__cuil__icontains=query_clean)) &
                ~Q(persona__cuil__isnull=True) &
                ~Q(persona__cuil__exact='')
            )

        alumnos = alumnos.filter(filtros_q).distinct()

    # Filtro por Carrera
    if carrera_id:
        alumnos = alumnos.filter(cursadas__comision__plan_estudio__carrera__codigo_carrera=carrera_id).distinct()

    # Filtro por Año de Cursada
    if anio_filtro and anio_filtro.isdigit():
        alumnos = alumnos.filter(cursadas__comision__plan_estudio__anio_carrera=int(anio_filtro)).distinct()

    # Filtro por Localidad
    if localidad_filtro:
        alumnos = alumnos.filter(persona__localidad__icontains=localidad_filtro)

    carreras = Carrera.objects.all().order_by('nombre_carrera')
    localidades = Persona.objects.exclude(localidad__isnull=True).exclude(localidad__exact='').values_list('localidad', flat=True).distinct().order_by('localidad')

    alumnos_list = []
    for al in alumnos:
        cursadas = al.cursadas.all()
        carreras_dict = {}
        for c in cursadas:
            if c.comision and c.comision.plan_estudio:
                c_nom = c.comision.plan_estudio.carrera.nombre_carrera
                c_an = c.comision.plan_estudio.anio_carrera
                if c_nom not in carreras_dict:
                    carreras_dict[c_nom] = set()
                carreras_dict[c_nom].add(c_an)

        carreras_formatted_list = []
        for c_nom, anios_set in sorted(carreras_dict.items()):
            anios_sorted = sorted(list(anios_set), key=lambda x: int(str(x).replace('°', '').replace('º', '')) if str(x).isdigit() or str(x).replace('°','').replace('º','').isdigit() else 0)
            if len(anios_sorted) == 1:
                anios_str = f"{anios_sorted[0]}° Año"
            elif len(anios_sorted) == 2:
                anios_str = f"{anios_sorted[0]}° y {anios_sorted[1]}° Año"
            else:
                anios_str = f"{', '.join(f'{a}°' for a in anios_sorted[:-1])} y {anios_sorted[-1]}° Año"
            carreras_formatted_list.append(f"{c_nom} ({anios_str})")

        promocionadas = sum(1 for c in cursadas if c.situacion_final == 'Promocionado')
        regulares = sum(1 for c in cursadas if c.situacion_final == 'Regular')
        finales = sum(1 for c in cursadas if c.situacion_final == 'Final')
        libres = sum(1 for c in cursadas if c.situacion_final == 'Libre')

        # Calificaciones promedio
        notas_list = []
        for c in cursadas:
            for ev in c.evaluaciones.all():
                if ev.nota is not None:
                    notas_list.append(float(ev.nota))
        promedio = round(sum(notas_list) / len(notas_list), 2) if notas_list else None

        alumnos_list.append({
            'alumno': al,
            'persona': al.persona,
            'edad': al.persona.edad,
            'carreras': ", ".join(carreras_formatted_list) if carreras_formatted_list else "Sin Inscripción Activa",
            'localidad': al.persona.localidad or 'Sin registrar',
            'cuil': al.persona.cuil or '-',
            'total_cursadas': cursadas.count(),
            'promocionadas': promocionadas,
            'regulares': regulares,
            'finales': finales,
            'libres': libres,
            'promedio': promedio,
        })

    # Criterios de Ordenamiento
    if orden_filtro == 'nombre':
        alumnos_list.sort(key=lambda x: (x['persona'].nombre or '').lower())
    elif orden_filtro == 'dni':
        alumnos_list.sort(key=lambda x: int(x['persona'].dni) if x['persona'].dni.isdigit() else 0)
    elif orden_filtro == 'carrera':
        alumnos_list.sort(key=lambda x: x['carreras'].lower())
    elif orden_filtro == 'edad_asc':
        alumnos_list.sort(key=lambda x: (x['edad'] is None, x['edad']))
    elif orden_filtro == 'edad_desc':
        alumnos_list.sort(key=lambda x: (x['edad'] is None, -(x['edad'] or 0)))
    elif orden_filtro == 'localidad':
        alumnos_list.sort(key=lambda x: (x['localidad'] or '').lower())
    else:
        alumnos_list.sort(key=lambda x: (x['persona'].apellido or '').lower())

    # Paginación estandarizada
    paginator = Paginator(alumnos_list, page_size)
    page_obj = paginator.get_page(page_num)

    context = {
        'query': query,
        'carrera_id': carrera_id,
        'anio_filtro': anio_filtro,
        'localidad_filtro': localidad_filtro,
        'orden_filtro': orden_filtro,
        'page_size': page_size,
        'page_obj': page_obj,
        'alumnos_list': page_obj.object_list,
        'carreras': carreras,
        'localidades': localidades,
        'total_resultados': len(alumnos_list),
        'total_alumnos_sistema': Alumno.objects.count(),
        'total_carreras_sistema': Carrera.objects.count(),
        'total_cursadas_sistema': Cursada.objects.count(),
        'total_evaluaciones_sistema': Evaluacion.objects.count(),
    }
    return render(request, 'gestion/buscador.html', context)


@csrf_protect
def alumno_detalle_json(request, dni):
    dni_clean = str(dni).replace('.', '').replace(' ', '').replace('-', '').strip()[:20]
    persona = get_object_or_404(Persona, dni=dni_clean)
    alumno = get_object_or_404(Alumno, persona=persona)
    
    cursadas_qs = Cursada.objects.filter(alumno=alumno).select_related(
        'comision__plan_estudio__carrera',
        'comision__plan_estudio__materia'
    ).prefetch_related('evaluaciones', 'comision__docentes_asignados__docente__persona')

    carreras_dict = {}
    total_notas = 0
    cant_notas = 0

    cursadas_data = []
    for c in cursadas_qs:
        materia_name = c.comision.plan_estudio.materia.nombre_materia if c.comision and c.comision.plan_estudio else "Materia Indefinida"
        carrera_name = c.comision.plan_estudio.carrera.nombre_carrera if c.comision and c.comision.plan_estudio else "Sin Carrera"
        anio_carrera = c.comision.plan_estudio.anio_carrera if c.comision and c.comision.plan_estudio else 1

        if carrera_name not in carreras_dict:
            carreras_dict[carrera_name] = set()
        carreras_dict[carrera_name].add(f"{anio_carrera}° Año")

        docentes_list = [f"{d.docente.persona.apellido}, {d.docente.persona.nombre}" for d in c.comision.docentes_asignados.all()]
        docentes_str = ", ".join(docentes_list) if docentes_list else "A designar"

        evals_data = []
        nota_final_val = None
        for ev in c.evaluaciones.all():
            evals_data.append({
                'instancia': ev.instancia,
                'nota': float(ev.nota) if ev.nota is not None else None,
                'fecha': ev.fecha.strftime('%d/%m/%Y') if ev.fecha else ''
            })
            if ev.nota is not None:
                total_notas += float(ev.nota)
                cant_notas += 1
                if ev.instancia == 'Nota Final':
                    nota_final_val = float(ev.nota)

        cursadas_data.append({
            'id_cursada': c.id_cursada,
            'carrera': carrera_name,
            'materia': materia_name,
            'anio_carrera': anio_carrera,
            'comision': c.comision.codigo_comision if c.comision else '-',
            'docentes': docentes_str,
            'situacion': c.situacion_final,
            'nota_final': nota_final_val,
            'evaluaciones': evals_data
        })

    cant_cursadas = len(cursadas_data)
    promedio_notas = round(total_notas / cant_notas, 2) if cant_notas > 0 else "N/A"

    carreras_formatted = []
    for car, ans in sorted(carreras_dict.items()):
        ans_sorted = sorted(list(ans), key=lambda x: int(str(x).replace('°', '').replace('º', '')) if str(x).isdigit() or str(x).replace('°','').replace('º','').isdigit() else 0)
        if len(ans_sorted) == 1:
            ans_str = f"{ans_sorted[0]}° Año"
        elif len(ans_sorted) == 2:
            ans_str = f"{ans_sorted[0]}° y {ans_sorted[1]}° Año"
        else:
            ans_str = f"{', '.join(f'{a}°' for a in ans_sorted[:-1])} y {ans_sorted[-1]}° Año"
        carreras_formatted.append(f"{car} ({ans_str})")

    data = {
        'personal': {
            'dni': persona.dni,
            'cuil': persona.cuil or '',
            'nombre': persona.nombre,
            'apellido': persona.apellido,
            'nombre_completo': f"{persona.apellido}, {persona.nombre}",
            'legajo': alumno.legajo or f"LEG-{persona.dni}",
            'fecha_nacimiento': persona.fecha_nacimiento.strftime('%d/%m/%Y') if persona.fecha_nacimiento else '',
            'edad': persona.edad if persona.edad is not None else '',
            'genero_sigla': persona.identidad,
            'genero_desc': persona.genero_descripcion,
            'nacionalidad': persona.nacionalidad or '',
            'mail': persona.mail or '',
            'domicilio': persona.domicilio or '',
            'localidad': persona.localidad or '',
            'telefono': persona.telefono or ''
        },
        'resumen_academico': {
            'carreras': carreras_formatted,
            'total_materias_cursadas': cant_cursadas,
            'promedio_notas': promedio_notas,
            'aprobadas_promocionadas': sum(1 for c in cursadas_data if c['situacion'] == 'Promocionado'),
            'a_final': sum(1 for c in cursadas_data if c['situacion'] == 'Final'),
            'regulares': sum(1 for c in cursadas_data if c['situacion'] == 'Regular'),
            'libres': sum(1 for c in cursadas_data if c['situacion'] == 'Libre'),
        },
        'cursadas': cursadas_data
    }
    return JsonResponse(data)


@csrf_protect
def imprimir_estado_academico(request, dni):
    dni_clean = str(dni).replace('.', '').replace(' ', '').replace('-', '').strip()[:20]
    persona = get_object_or_404(Persona, dni=dni_clean)
    alumno = get_object_or_404(Alumno, persona=persona)
    cursadas = Cursada.objects.filter(alumno=alumno).select_related(
        'comision__plan_estudio__carrera',
        'comision__plan_estudio__materia'
    ).prefetch_related('evaluaciones', 'comision__docentes_asignados__docente__persona')

    context = {
        'persona': persona,
        'alumno': alumno,
        'cursadas': cursadas,
        'fecha_emision': datetime.date.today().strftime('%d/%m/%Y')
    }
    return render(request, 'gestion/imprimir_analitico.html', context)


@csrf_protect
def descargar_libro_matriz(request, codigo_carrera=None):
    """
    Descarga el Libro Matriz oficial en formato Excel (.xlsx) para la carrera solicitada.
    """
    cod = codigo_carrera or request.GET.get('carrera') or request.POST.get('carrera')
    if cod:
        carrera_obj = get_object_or_404(Carrera, codigo_carrera=cod)
    else:
        carrera_obj = Carrera.objects.filter(codigo_carrera='ENERGIA-794').first() or Carrera.objects.first()
        if not carrera_obj:
            raise Http404("No hay carreras registradas en el sistema.")

    excel_stream = generar_libro_matriz_excel(carrera_obj)
    nombre_archivo_limpio = "".join(c for c in carrera_obj.nombre_carrera if c.isalnum() or c in (' ', '_', '-')).rstrip()
    filename = f"LIBRO_MATRIZ_{nombre_archivo_limpio.replace(' ', '_')}.xlsx"
    
    response = HttpResponse(
        excel_stream.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def descargar_plantilla_alumnos(request):
    """
    Descarga la plantilla Excel (.xlsx) oficial formateada para la carga de alumnos.
    """
    from .excel_import_export import generar_plantilla_alumnos_excel
    excel_stream = generar_plantilla_alumnos_excel()
    filename = "Plantilla_Carga_Alumnos_ISFT188.xlsx"
    response = HttpResponse(
        excel_stream.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@csrf_protect
def importar_alumnos_view(request):
    """
    Procesa la subida de un archivo Excel (.xlsx/.xls) para importar o actualizar alumnos.
    Retorna el resultado en formato JSON para visualización interactiva con reporte de errores.
    """
    from .excel_import_export import procesar_importacion_alumnos_excel

    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensaje': 'Método no permitido. Se requiere POST.'}, status=405)

    archivo = request.FILES.get('archivo_excel')
    if not archivo:
        return JsonResponse({'success': False, 'mensaje': 'No se seleccionó ningún archivo Excel para subir.'}, status=400)

    if not (archivo.name.endswith('.xlsx') or archivo.name.endswith('.xls')):
        return JsonResponse({'success': False, 'mensaje': 'El archivo debe tener extensión .xlsx o .xls.'}, status=400)

    resultado = procesar_importacion_alumnos_excel(archivo)
    return JsonResponse(resultado)

