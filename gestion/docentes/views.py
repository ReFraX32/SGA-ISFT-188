# --------------------------------------------------------------------------
# MÓDULO: Gestión de Docentes — VISTAS
# --------------------------------------------------------------------------
# Este archivo vive en gestion/docentes/views.py, separado del resto de
# gestion/views.py. Se conecta con el sistema principal a través de
# gestion/urls.py, que importa este módulo y registra sus rutas.
# --------------------------------------------------------------------------

import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from gestion.models import Docente, Persona, ComisionDocente
from gestion.forms import DocenteForm
from gestion.views import (
    formatear_dni,
    formatear_cuil,
    formatear_telefono,
    formatear_carreras_con_resolucion,
)
from .excel_import import procesar_importacion_docentes_excel

DOCENTES_SESSION_KEY = 'carga_docentes_temp_data_list'
DOCENTES_EDIT_KEY = 'carga_docentes_edit_data'


def get_docentes_sesion(request):
    data = request.session.get(DOCENTES_SESSION_KEY, [])
    if isinstance(data, dict):
        return [data] if data else []
    if isinstance(data, list):
        return data
    return []


@login_required(login_url='login:login')
@csrf_protect
def docentes_view(request):
    """Módulo de búsqueda, filtrado y consulta de docentes."""
    req_data = request.POST if request.method == 'POST' else request.GET

    query = req_data.get('q', '').strip()[:100]
    genero_filtro = req_data.get('genero', '').strip()
    nacionalidad_filtro = req_data.get('nacionalidad', '').strip()
    localidad_filtro = req_data.get('localidad', '').strip()
    orden_filtro = req_data.get('orden', 'apellido').strip()
    page_num = req_data.get('page', '1').strip()
    page_size_val = req_data.get('page_size', '25').strip()

    try:
        page_size = int(page_size_val)
        if page_size not in [10, 25, 50, 100]:
            page_size = 25
    except (ValueError, TypeError):
        page_size = 25

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

    if genero_filtro:
        docentes = docentes.filter(persona__identidad=genero_filtro)

    if nacionalidad_filtro:
        docentes = docentes.filter(persona__nacionalidad__iexact=nacionalidad_filtro)

    if localidad_filtro:
        docentes = docentes.filter(persona__localidad__iexact=localidad_filtro)

    # Mapeo de ordenamiento
    orden_map = {
        'apellido': ['persona__apellido', 'persona__nombre'],
        'nombre': ['persona__nombre', 'persona__apellido'],
        'dni': ['persona__dni'],
        'titulo': ['titulo_mn', 'persona__apellido'],
        'localidad': ['persona__localidad', 'persona__apellido'],
        'nacionalidad': ['persona__nacionalidad', 'persona__apellido'],
        'edad_asc': ['-persona__fecha_nacimiento', 'persona__apellido'],
        'edad_desc': ['persona__fecha_nacimiento', 'persona__apellido'],
    }
    criterio_orden = orden_map.get(orden_filtro, ['persona__apellido', 'persona__nombre'])
    docentes = docentes.order_by(*criterio_orden)

    # Opciones dinámicas para selectores
    todas_nacionalidades = (
        Persona.objects.exclude(nacionalidad__isnull=True)
        .exclude(nacionalidad='')
        .values_list('nacionalidad', flat=True)
        .distinct()
        .order_by('nacionalidad')
    )
    todas_localidades = (
        Persona.objects.exclude(localidad__isnull=True)
        .exclude(localidad='')
        .values_list('localidad', flat=True)
        .distinct()
        .order_by('localidad')
    )

    paginator = Paginator(docentes, page_size)
    page_obj = paginator.get_page(page_num)

    for doc in page_obj:
        doc.dni_formateado = formatear_dni(doc.persona.dni)
        doc.cuil_formateado = formatear_cuil(doc.persona.cuil)

    return render(request, 'gestion/docentes.html', {
        'query': query,
        'genero_filtro': genero_filtro,
        'generos_choices': Persona.GENERO_CHOICES,
        'nacionalidad_filtro': nacionalidad_filtro,
        'nacionalidades': list(todas_nacionalidades),
        'localidad_filtro': localidad_filtro,
        'localidades': list(todas_localidades),
        'orden_filtro': orden_filtro,
        'page_size': page_size,
        'page_obj': page_obj,
        'docentes': page_obj.object_list,
        'total_resultados': paginator.count,
    })


@login_required(login_url='login:login')
@csrf_protect
def alta_docente_view(request):
    """
    Formulario guiado para el alta individual de un docente.
    Guarda en la matriz de sesión y redirige al Paso 2 de confirmación.
    """
    docentes_acumulados = get_docentes_sesion(request)

    if request.method == 'POST':
        form = DocenteForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data.copy()
            fecha_val = cleaned.get('fecha_nacimiento')
            if isinstance(fecha_val, (datetime.date, datetime.datetime)):
                cleaned['fecha_nacimiento'] = fecha_val.strftime('%Y-%m-%d')

            dni_nuevo = cleaned.get('dni')
            cuil_nuevo = cleaned.get('cuil')

            if any(d.get('dni') == dni_nuevo for d in docentes_acumulados):
                messages.error(request, f"El/la docente con DNI {dni_nuevo} ya fue ingresado/a en esta tanda de carga.")
                return render(request, 'gestion/docentes/alta.html', {
                    'form': form,
                    'total_en_matriz': len(docentes_acumulados),
                    'hay_borrador_pendiente': bool(docentes_acumulados),
                })

            if cuil_nuevo and any(d.get('cuil') == cuil_nuevo for d in docentes_acumulados):
                messages.error(request, f"El CUIL {cuil_nuevo} ya fue ingresado para otro docente en esta misma tanda.")
                return render(request, 'gestion/docentes/alta.html', {
                    'form': form,
                    'total_en_matriz': len(docentes_acumulados),
                    'hay_borrador_pendiente': bool(docentes_acumulados),
                })

            docentes_acumulados.append(cleaned)
            request.session[DOCENTES_SESSION_KEY] = docentes_acumulados
            request.session.modified = True

            messages.success(
                request,
                f"Docente {cleaned.get('apellido')}, {cleaned.get('nombre')} incorporado/a a la matriz de verificación."
            )
            return redirect(reverse('gestion:paso2_confirmacion_docentes'))
        else:
            messages.error(
                request,
                "Por favor, revisá los campos señalados en rojo para corregir los datos ingresados."
            )
    else:
        datos_edit = request.session.pop(DOCENTES_EDIT_KEY, None)
        if datos_edit:
            request.session.modified = True
            form = DocenteForm(initial=datos_edit)
        else:
            form = DocenteForm()

    return render(request, 'gestion/docentes/alta.html', {
        'form': form,
        'total_en_matriz': len(docentes_acumulados),
        'hay_borrador_pendiente': bool(docentes_acumulados),
    })


@login_required(login_url='login:login')
@csrf_protect
def paso2_confirmacion_docentes(request):
    """
    Paso 2: Previsualización en matriz de datos completa y confirmación para Docentes.
    Permite visualizar uno o más docentes en una matriz completa.
    """
    docentes_lista = get_docentes_sesion(request)

    if not docentes_lista:
        messages.warning(request, "No hay ningún docente en la matriz de carga. Ingresá los datos primero.")
        return redirect(reverse('gestion:alta_docente'))

    genero_dict = dict(Persona.GENERO_CHOICES)
    docentes_matriz = []
    for idx, item in enumerate(docentes_lista):
        copia = item.copy()
        copia['fila_num'] = idx + 1
        copia['fila_index'] = idx
        copia['genero_humano'] = genero_dict.get(item.get('identidad', ''), item.get('identidad', ''))
        copia['dni_formateado'] = formatear_dni(item.get('dni'))
        copia['cuil_formateado'] = formatear_cuil(item.get('cuil'))
        copia['telefono_formateado'] = formatear_telefono(item.get('telefono'))
        docentes_matriz.append(copia)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'confirmar':
            guardados_ok = 0
            errores = []

            for datos in docentes_lista:
                dni_candidato = str(datos.get('dni', '')).strip()
                cuil_candidato = str(datos.get('cuil', '')).strip()

                if Persona.objects.filter(dni=dni_candidato).exists():
                    errores.append(f"DNI {dni_candidato} ya existe en la base de datos.")
                    continue
                if cuil_candidato and Persona.objects.filter(cuil=cuil_candidato).exists():
                    errores.append(f"CUIL {cuil_candidato} ya existe en la base de datos.")
                    continue

                fnac = datos.get('fecha_nacimiento')
                if isinstance(fnac, str) and fnac:
                    try:
                        fnac = datetime.datetime.strptime(fnac, '%Y-%m-%d').date()
                    except ValueError:
                        fnac = None

                persona = Persona.objects.create(
                    dni=dni_candidato,
                    cuil=cuil_candidato or None,
                    nombre=datos.get('nombre', '').strip(),
                    apellido=datos.get('apellido', '').strip(),
                    fecha_nacimiento=fnac,
                    identidad=datos.get('identidad', 'N'),
                    nacionalidad=datos.get('nacionalidad', 'Argentina') or 'Argentina',
                    localidad=datos.get('localidad', '') or None,
                    domicilio=datos.get('domicilio', '') or None,
                    telefono=datos.get('telefono', '') or None,
                    mail=datos.get('mail', '') or None,
                )
                Docente.objects.create(
                    persona=persona,
                    titulo_mn=datos.get('titulo_mn', '').strip() or None
                )
                guardados_ok += 1

            request.session.pop(DOCENTES_SESSION_KEY, None)
            request.session.modified = True

            if guardados_ok > 0:
                messages.success(
                    request,
                    f"¡Excelente! Se confirmaron y guardaron exitosamente {guardados_ok} docente{'s' if guardados_ok != 1 else ''} en el sistema."
                )
            if errores:
                for err in errores:
                    messages.error(request, err)

            return redirect(reverse('gestion:docentes'))

        elif accion == 'nuevo_docente':
            return redirect(reverse('gestion:alta_docente'))

        elif accion == 'modificar':
            if docentes_lista:
                ultimo = docentes_lista.pop()
                request.session[DOCENTES_SESSION_KEY] = docentes_lista
                request.session[DOCENTES_EDIT_KEY] = ultimo
                request.session.modified = True
            return redirect(reverse('gestion:alta_docente'))

        elif accion == 'editar_fila':
            try:
                fila_idx = int(request.POST.get('fila_index', -1))
                if 0 <= fila_idx < len(docentes_lista):
                    elegido = docentes_lista.pop(fila_idx)
                    request.session[DOCENTES_SESSION_KEY] = docentes_lista
                    request.session[DOCENTES_EDIT_KEY] = elegido
                    request.session.modified = True
            except (ValueError, TypeError):
                pass
            return redirect(reverse('gestion:alta_docente'))

        elif accion == 'eliminar_fila':
            try:
                fila_idx = int(request.POST.get('fila_index', -1))
                if 0 <= fila_idx < len(docentes_lista):
                    eliminado = docentes_lista.pop(fila_idx)
                    request.session[DOCENTES_SESSION_KEY] = docentes_lista
                    request.session.modified = True
                    messages.info(
                        request,
                        f"Docente {eliminado.get('apellido')}, {eliminado.get('nombre')} quitado/a de la matriz."
                    )
            except (ValueError, TypeError):
                pass

            if not docentes_lista:
                return redirect(reverse('gestion:alta_docente'))
            return redirect(reverse('gestion:paso2_confirmacion_docentes'))

        elif accion == 'cancelar':
            request.session.pop(DOCENTES_SESSION_KEY, None)
            request.session.pop(DOCENTES_EDIT_KEY, None)
            request.session.modified = True
            messages.info(request, "Se descartó la matriz de docentes.")
            return redirect(reverse('gestion:alta_docente'))

    return render(request, 'gestion/docentes/paso2_confirmacion.html', {
        'docentes_matriz': docentes_matriz,
        'total_docentes': len(docentes_matriz),
    })


@login_required(login_url='login:login')
@csrf_protect
def docente_detalle_json(request, dni):
    dni_clean = str(dni).replace('.', '').replace(' ', '').replace('-', '').strip()[:20]
    persona = get_object_or_404(Persona, dni=dni_clean)
    docente = get_object_or_404(Docente, persona=persona)

    comisiones_qs = ComisionDocente.objects.filter(docente=docente).select_related(
        'comision__plan_estudio__carrera',
        'comision__plan_estudio__materia'
    ).prefetch_related('comision__cursadas')

    carreras_dict = {}
    materias_set = set()
    total_alumnos = 0
    comisiones_data = []

    for cd in comisiones_qs:
        com = cd.comision
        plan = com.plan_estudio if com else None
        car = plan.carrera if plan else None
        mat = plan.materia if plan else None

        carrera_name = car.nombre_carrera if car else "Sin Carrera"
        carrera_res = car.resolucion_vigente if car else ""
        materia_name = mat.nombre_materia if mat else "Materia Indefinida"
        anio_carrera = plan.anio_carrera if plan else 1

        if car:
            key = (carrera_name, carrera_res)
            if key not in carreras_dict:
                carreras_dict[key] = set()
            carreras_dict[key].add(anio_carrera)

        if mat:
            materias_set.add(materia_name)

        cant_inscriptos = com.cursadas.count() if com else 0
        total_alumnos += cant_inscriptos

        comisiones_data.append({
            'comision': com.codigo_comision if com else '-',
            'materia': materia_name,
            'carrera': f"{carrera_name} ({carrera_res})" if carrera_res else carrera_name,
            'anio_carrera': anio_carrera,
            'turno': com.turno if com else '-',
            'division': com.division if com else '-',
            'rol': cd.rol,
            'alumnos_inscriptos': cant_inscriptos,
        })

    carreras_formatted = formatear_carreras_con_resolucion(carreras_dict)

    data = {
        'personal': {
            'dni': formatear_dni(persona.dni),
            'dni_raw': persona.dni,
            'cuil': formatear_cuil(persona.cuil),
            'nombre': persona.nombre,
            'apellido': persona.apellido,
            'nombre_completo': f"Prof. {persona.apellido}, {persona.nombre}",
            'titulo_mn': docente.titulo_mn or 'Sin título/matrícula registrada',
            'fecha_nacimiento': persona.fecha_nacimiento.strftime('%d/%m/%Y') if persona.fecha_nacimiento else '',
            'edad': persona.edad if persona.edad is not None else '',
            'genero_sigla': persona.identidad,
            'genero_desc': persona.genero_descripcion,
            'nacionalidad': persona.nacionalidad or 'Argentina',
            'mail': persona.mail or '',
            'domicilio': persona.domicilio or '',
            'localidad': persona.localidad or '',
            'telefono': formatear_telefono(persona.telefono),
        },
        'resumen_docente': {
            'total_comisiones': len(comisiones_data),
            'total_materias': len(materias_set),
            'carreras': carreras_formatted,
            'total_alumnos_a_cargo': total_alumnos,
        },
        'comisiones': comisiones_data,
    }
    return JsonResponse(data)



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


@login_required(login_url='login:login')
def imprimir_ficha_docente(request, dni: str):
    """
    Vista oficial para imprimir la ficha de legajo institucional del docente,
    estructurada de manera idéntica al analítico de alumnos.
    """
    dni_clean = str(dni).replace('.', '').replace(' ', '').replace('-', '').strip()[:20]
    persona = get_object_or_404(Persona, dni=dni_clean)
    docente = get_object_or_404(Docente, persona=persona)
    comisiones_doc = ComisionDocente.objects.filter(docente=docente).select_related(
        'comision__plan_estudio__carrera',
        'comision__plan_estudio__materia'
    ).order_by('-comision__anio_lectivo', 'comision__plan_estudio__carrera__nombre_carrera', 'comision__plan_estudio__materia__nombre_materia')

    materias_set = set()
    carreras_set = set()
    for cd in comisiones_doc:
        pe = cd.comision.plan_estudio
        materias_set.add(pe.materia.nombre_materia)
        carreras_set.add(pe.carrera.nombre_carrera)

    context = {
        'persona': persona,
        'docente': docente,
        'dni_formateado': formatear_dni(persona.dni),
        'cuil_formateado': formatear_cuil(persona.cuil),
        'telefono_formateado': formatear_telefono(persona.telefono),
        'comisiones_doc': comisiones_doc,
        'total_comisiones': comisiones_doc.count(),
        'total_materias': len(materias_set),
        'total_carreras': len(carreras_set),
        'fecha_emision': datetime.date.today().strftime('%d/%m/%Y'),
    }
    return render(request, 'gestion/docentes/imprimir_docente.html', context)

