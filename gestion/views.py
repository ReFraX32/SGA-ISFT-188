import datetime
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse, Http404
from django.db.models import Q, Avg, Count
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Alumno, Persona, Cursada, Carrera, PlanEstudio, Evaluacion
from .libro_matriz import generar_libro_matriz_excel

def formatear_dni(dni):
    if not dni:
        return "-"
    digits = "".join(c for c in str(dni) if c.isdigit())
    if not digits:
        return str(dni)
    return f"{int(digits):,}".replace(",", ".")

def formatear_cuil(cuil):
    if not cuil or str(cuil).strip() in ['', 'None', '-', '--']:
        return "-"
    digits = "".join(c for c in str(cuil) if c.isdigit())
    if len(digits) == 11:
        return f"{digits[:2]}-{digits[2:10]}-{digits[10]}"
    return str(cuil)

def formatear_telefono(tel):
    if not tel or str(tel).strip() in ['', 'None', '-', '--']:
        return "-"
    digits = "".join(c for c in str(tel) if c.isdigit())
    if not digits:
        return str(tel)
    if digits.startswith('549'):
        digits = digits[3:]
    elif digits.startswith('54'):
        digits = digits[2:]
    if digits.startswith('0'):
        digits = digits[1:]
    
    if len(digits) == 10:
        if digits.startswith('11'):
            return f"+54 9 11 {digits[2:6]}-{digits[6:]}"
        else:
            return f"+54 9 {digits[:3]} {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 8:
        return f"+54 9 11 {digits[:4]}-{digits[4:]}"
    return f"+54 9 {digits}"

def formatear_carreras_con_resolucion(carreras_dict):
    """
    Formatea las carreras incluyendo su resolución y los años agrupados correctamente.
    Ejemplo:
    - 'Técnico Superior en Energía con Orientación Industrial (Res. 794/01) (1°, 2° y 3° Año)'
    - 'Tecnicatura Superior en Higiene y Seguridad en el Trabajo (Res. 320/13) (1° Año)'
    """
    resultado = []
    for (c_nom, c_res), anios_set in sorted(carreras_dict.items(), key=lambda x: x[0][0]):
        anios_clean = []
        for a in anios_set:
            digits = "".join(c for c in str(a) if c.isdigit())
            if digits:
                anios_clean.append(int(digits))
        anios_sorted = sorted(list(set(anios_clean)))
        
        if len(anios_sorted) == 1:
            anios_str = f"{anios_sorted[0]}° Año"
        elif len(anios_sorted) == 2:
            anios_str = f"{anios_sorted[0]}° y {anios_sorted[1]}° Año"
        elif len(anios_sorted) > 2:
            anios_str = f"{', '.join(f'{a}°' for a in anios_sorted[:-1])} y {anios_sorted[-1]}° Año"
        else:
            anios_str = "Año s/d"

        res_str = f" ({c_res})" if c_res and str(c_res).strip() not in ['', 'None', '-'] else ""
        resultado.append(f"{c_nom}{res_str} ({anios_str})")
    return resultado

@login_required(login_url='login:login')
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

    # Busqueda flexible por DNI (limpio/con puntos), CUIL, Nombre, Apellido, Legajo o Localidad
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

    carreras = Carrera.objects.all().order_by('nombre_carrera', 'resolucion_vigente')
    localidades = Persona.objects.exclude(localidad__isnull=True).exclude(localidad__exact='').values_list('localidad', flat=True).distinct().order_by('localidad')

    alumnos_list = []
    for al in alumnos:
        cursadas = al.cursadas.all()
        carreras_dict = {}
        for c in cursadas:
            if c.comision and c.comision.plan_estudio and c.comision.plan_estudio.carrera:
                car = c.comision.plan_estudio.carrera
                c_nom = car.nombre_carrera
                c_res = car.resolucion_vigente
                c_an = c.comision.plan_estudio.anio_carrera
                key = (c_nom, c_res)
                if key not in carreras_dict:
                    carreras_dict[key] = set()
                carreras_dict[key].add(c_an)

        carreras_formatted_list = formatear_carreras_con_resolucion(carreras_dict)

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
            'dni_formateado': formatear_dni(al.persona.dni),
            'cuil_formateado': formatear_cuil(al.persona.cuil),
            'telefono_formateado': formatear_telefono(al.persona.telefono),
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

    # Paginacion estandarizada
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
        'total_resultados': len(alumnos_list),
        'carreras': carreras,
        'localidades': localidades,
    }
    return render(request, 'gestion/buscador.html', context)


@login_required(login_url='login:login')
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
        car = c.comision.plan_estudio.carrera if c.comision and c.comision.plan_estudio else None
        materia_name = c.comision.plan_estudio.materia.nombre_materia if c.comision and c.comision.plan_estudio and c.comision.plan_estudio.materia else "Materia Indefinida"
        carrera_name = car.nombre_carrera if car else "Sin Carrera"
        carrera_res = car.resolucion_vigente if car else ""
        anio_carrera = c.comision.plan_estudio.anio_carrera if c.comision and c.comision.plan_estudio else 1

        if car:
            key = (carrera_name, carrera_res)
            if key not in carreras_dict:
                carreras_dict[key] = set()
            carreras_dict[key].add(anio_carrera)

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
            'carrera': f"{carrera_name} ({carrera_res})" if carrera_res else carrera_name,
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

    carreras_formatted = formatear_carreras_con_resolucion(carreras_dict)

    data = {
        'personal': {
            'dni': formatear_dni(persona.dni),
            'dni_raw': persona.dni,
            'cuil': formatear_cuil(persona.cuil),
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
            'telefono': formatear_telefono(persona.telefono)
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


@login_required(login_url='login:login')
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
        'dni_formateado': formatear_dni(persona.dni),
        'cuil_formateado': formatear_cuil(persona.cuil),
        'telefono_formateado': formatear_telefono(persona.telefono),
        'cursadas': cursadas,
        'fecha_emision': datetime.date.today().strftime('%d/%m/%Y')
    }
    return render(request, 'gestion/imprimir_analitico.html', context)


@login_required(login_url='login:login')
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


@login_required(login_url='login:login')
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


@login_required(login_url='login:login')
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
