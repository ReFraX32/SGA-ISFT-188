import json
from decimal import Decimal
from typing import Any, Dict, List
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.db.models import Count, Q, Sum, Min, Max
from django.core.paginator import Paginator
from django.contrib import messages

from gestion.models import Carrera, Materia, PlanEstudio, Comision
from login.decorators import directivo_required
from .forms import CarreraForm, CarreraEditForm

CARRERA_SESSION_KEY = 'carrera_borrador_datos'
MATRIZ_SESSION_KEY = 'carrera_borrador_materias'


@directivo_required
def carreras_list_view(request):
    """
    Vista principal del módulo de carreras: listado, búsqueda avanzada,
    filtros por estado de materias y ordenamiento con paginación.
    """
    if request.GET.get('limpiar') == '1' or (request.method == 'POST' and request.POST.get('limpiar') == '1'):
        request.session.pop('carreras_filtros_guardados', None)
        return redirect('carreras:carreras_list')

    if request.method == 'POST':
        request.session['carreras_filtros_guardados'] = {
            'q': request.POST.get('q', '').strip(),
            'con_materias': request.POST.get('con_materias', 'todas'),
            'orden': request.POST.get('orden', 'nombre'),
            'page_size': request.POST.get('page_size', '10'),
            'page': request.POST.get('page', '1'),
        }
        return redirect('carreras:carreras_list')

    filtros_guardados = request.session.get('carreras_filtros_guardados', {})
    query = request.GET.get('q', filtros_guardados.get('q', '')).strip()
    con_materias = request.GET.get('con_materias', filtros_guardados.get('con_materias', 'todas'))
    orden = request.GET.get('orden', filtros_guardados.get('orden', 'nombre'))
    page_req = request.GET.get('page', filtros_guardados.get('page', 1))
    page_size_req = request.GET.get('page_size', filtros_guardados.get('page_size', 10))

    try:
        page_size = int(page_size_req)
        if page_size not in [10, 25, 50, 100]:
            page_size = 10
    except (ValueError, TypeError):
        page_size = 10

    carreras = Carrera.objects.annotate(
        total_materias=Count('planes_estudio', distinct=True),
        anio_min=Min('planes_estudio__anio_carrera'),
        anio_max=Max('planes_estudio__anio_carrera'),
        total_horas_anuales=Sum('planes_estudio__carga_horaria_anual')
    )

    if query:
        carreras = carreras.filter(
            Q(nombre_carrera__icontains=query) |
            Q(codigo_carrera__icontains=query) |
            Q(resolucion_vigente__icontains=query) |
            Q(resolucion_anterior__icontains=query)
        )

    if con_materias == 'con_materias':
        carreras = carreras.filter(total_materias__gt=0)
    elif con_materias == 'sin_materias':
        carreras = carreras.filter(total_materias=0)

    orden_map = {
        'nombre': ['nombre_carrera'],
        'codigo': ['codigo_carrera'],
        'materias_desc': ['-total_materias', 'nombre_carrera'],
        'materias_asc': ['total_materias', 'nombre_carrera'],
    }
    carreras = carreras.order_by(*orden_map.get(orden, ['nombre_carrera']))

    paginator = Paginator(carreras, page_size)
    page_obj = paginator.get_page(page_req)

    return render(request, 'carreras/carreras_list.html', {
        'query': query,
        'con_materias': con_materias,
        'orden': orden,
        'page_size': page_size,
        'page_obj': page_obj,
        'carreras': page_obj.object_list,
        'total_resultados': paginator.count,
    })


@directivo_required
def carrera_detalle_json(request, codigo_carrera: str):
    """
    Endpoint JSON que retorna los datos detallados de una carrera y su plan
    de estudios agrupado por año (Expediente de Carrera).
    """
    carrera = get_object_or_404(Carrera, codigo_carrera=codigo_carrera)
    planes = PlanEstudio.objects.filter(carrera=carrera).select_related('materia').order_by('anio_carrera', 'materia__nombre_materia')

    anios_dict: Dict[int, List[Dict[str, Any]]] = {}
    total_horas_anuales = 0
    total_horas_semanales = Decimal('0.0')

    for p in planes:
        anio = p.anio_carrera or 1
        if anio not in anios_dict:
            anios_dict[anio] = []

        hs_anuales = p.carga_horaria_anual or 0
        hs_semanales = p.carga_horaria_semanal or Decimal('0.0')
        total_horas_anuales += hs_anuales
        total_horas_semanales += hs_semanales

        anios_dict[anio].append({
            'id_plan': p.id_plan,
            'codigo_materia': p.materia.codigo_materia,
            'nombre_materia': p.materia.nombre_materia,
            'modalidad': p.modalidad or 'Anual',
            'carga_horaria_anual': hs_anuales,
            'carga_horaria_semanal': float(hs_semanales),
            'correlatividades': p.correlatividades or '',
        })

    # Convertir a lista estructurada ordenada por año
    anios_lista = []
    for anio in sorted(anios_dict.keys()):
        anios_lista.append({
            'numero': anio,
            'nombre': f"{anio}° Año",
            'materias': anios_dict[anio],
            'total_materias_anio': len(anios_dict[anio]),
        })

    return JsonResponse({
        'success': True,
        'codigo_carrera': carrera.codigo_carrera,
        'nombre_carrera': carrera.nombre_carrera,
        'resolucion_vigente': carrera.resolucion_vigente or 'Sin resolución registrada',
        'resolucion_anterior': carrera.resolucion_anterior or 'Ninguna',
        'total_materias': planes.count(),
        'total_horas_anuales': total_horas_anuales,
        'total_horas_semanales': float(total_horas_semanales),
        'anios': anios_lista,
    })


@directivo_required
@csrf_protect
def alta_carrera_view(request):
    """
    Paso 1: Formulario para ingresar los datos generales de la nueva carrera.
    Almacena el borrador en la sesión y avanza al Paso 2 (Matriz de Materias).
    """
    borrador = request.session.get(CARRERA_SESSION_KEY, {})

    if request.method == 'POST':
        form = CarreraForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data.copy()
            request.session[CARRERA_SESSION_KEY] = cleaned
            request.session.modified = True
            return redirect('carreras:alta_carrera_matriz')
    else:
        form = CarreraForm(initial=borrador)

    return render(request, 'carreras/alta_carrera.html', {
        'form': form,
        'hay_borrador': bool(borrador),
    })


@directivo_required
@csrf_protect
def alta_carrera_matriz_view(request):
    """
    Paso 2: Matriz interactiva de asignaturas agrupadas por año de carrera.
    Permite cargar y editar las materias ordenadas por año y guardar de forma atómica.
    """
    carrera_data = request.session.get(CARRERA_SESSION_KEY)
    if not carrera_data:
        messages.warning(request, "Primero completá los datos básicos de la carrera.")
        return redirect('carreras:alta_carrera')

    duracion = int(carrera_data.get('duracion_anios', 3))

    if request.method == 'POST':
        accion = request.POST.get('accion', 'guardar')

        if accion == 'volver':
            return redirect('carreras:alta_carrera')

        if accion == 'cancelar':
            request.session.pop(CARRERA_SESSION_KEY, None)
            request.session.pop(MATRIZ_SESSION_KEY, None)
            messages.info(request, "Carga de carrera cancelada.")
            return redirect('carreras:carreras_list')

        if accion == 'guardar':
            # Recolectar las materias enviadas en la matriz
            codigos = request.POST.getlist('materia_codigo[]')
            nombres = request.POST.getlist('materia_nombre[]')
            anios = request.POST.getlist('materia_anio[]')
            modalidades = request.POST.getlist('materia_modalidad[]')
            hs_semanales = request.POST.getlist('materia_hs_semanal[]')
            hs_anuales = request.POST.getlist('materia_hs_anual[]')
            correlatividades = request.POST.getlist('materia_correlatividades[]')

            materias_a_crear = []
            errores = []

            for i in range(len(codigos)):
                c_cod = codigos[i].strip().upper()
                c_nom = nombres[i].strip() if i < len(nombres) else ''
                c_anio_raw = anios[i].strip() if i < len(anios) else '1'
                c_mod = modalidades[i].strip() if i < len(modalidades) else 'Anual'
                c_sem_raw = hs_semanales[i].strip() if i < len(hs_semanales) else '0'
                c_anu_raw = hs_anuales[i].strip() if i < len(hs_anuales) else '0'
                c_corr = correlatividades[i].strip() if i < len(correlatividades) else ''

                if not c_cod and not c_nom:
                    continue  # Fila vacía ignorada

                if not c_cod:
                    errores.append(f"La materia en fila {i+1} no tiene código.")
                    continue
                if not c_nom:
                    errores.append(f"La materia con código '{c_cod}' no tiene nombre.")
                    continue

                try:
                    c_anio = int(c_anio_raw)
                except ValueError:
                    c_anio = 1

                try:
                    c_sem = Decimal(c_sem_raw.replace(',', '.')) if c_sem_raw else Decimal('0.0')
                except Exception:
                    c_sem = Decimal('0.0')

                semanas = 16 if 'cuatrimestre' in c_mod.lower() else 32
                c_anu = int(round(float(c_sem) * semanas))

                materias_a_crear.append({
                    'codigo_materia': c_cod,
                    'nombre_materia': c_nom,
                    'anio_carrera': c_anio,
                    'modalidad': c_mod or 'Anual',
                    'carga_horaria_semanal': c_sem,
                    'carga_horaria_anual': c_anu,
                    'correlatividades': c_corr,
                })

            if not materias_a_crear:
                errores.append("Debés ingresar al menos una materia en el plan de estudios.")

            if errores:
                for err in errores:
                    messages.error(request, err)
                return render(request, 'carreras/alta_carrera_matriz.html', {
                    'carrera': carrera_data,
                    'duracion': duracion,
                    'anios_rango': range(1, duracion + 1),
                    'materias_cargadas': materias_a_crear,
                })

            # Guardado atómico
            try:
                with transaction.atomic():
                    carrera = Carrera.objects.create(
                        codigo_carrera=carrera_data['codigo_carrera'],
                        nombre_carrera=carrera_data['nombre_carrera'],
                        resolucion_vigente=carrera_data.get('resolucion_vigente') or None,
                        resolucion_anterior=carrera_data.get('resolucion_anterior') or None,
                    )

                    for mat_info in materias_a_crear:
                        materia, _ = Materia.objects.get_or_create(
                            codigo_materia=mat_info['codigo_materia'],
                            defaults={'nombre_materia': mat_info['nombre_materia']}
                        )
                        PlanEstudio.objects.create(
                            carrera=carrera,
                            materia=materia,
                            anio_carrera=mat_info['anio_carrera'],
                            modalidad=mat_info['modalidad'],
                            carga_horaria_semanal=mat_info['carga_horaria_semanal'],
                            carga_horaria_anual=mat_info['carga_horaria_anual'],
                            correlatividades=mat_info['correlatividades'],
                        )

                # Limpieza de sesión
                request.session.pop(CARRERA_SESSION_KEY, None)
                request.session.pop(MATRIZ_SESSION_KEY, None)

                messages.success(
                    request,
                    f"¡Carrera '{carrera.nombre_carrera}' registrada exitosamente con {len(materias_a_crear)} materias en su plan de estudios!"
                )
                return redirect('carreras:carreras_list')

            except Exception as ex:
                messages.error(request, f"Ocurrió un error al guardar la carrera: {str(ex)}")

    return render(request, 'carreras/alta_carrera_matriz.html', {
        'carrera': carrera_data,
        'duracion': duracion,
        'anios_rango': range(1, duracion + 1),
        'materias_cargadas': [],
    })


@directivo_required
@csrf_protect
def carrera_editar_view(request, codigo_carrera: str):
    """
    Edición de datos de una carrera existente (nombre, resoluciones).
    Soporta peticiones AJAX retornando JSON y formularios tradicionales.
    """
    carrera = get_object_or_404(Carrera, codigo_carrera=codigo_carrera)

    if request.method == 'POST':
        form = CarreraEditForm(request.POST, instance=carrera)
        if form.is_valid():
            form.save()
            mensaje = f"Carrera '{carrera.nombre_carrera}' actualizada correctamente."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                return JsonResponse({'success': True, 'mensaje': mensaje})
            messages.success(request, mensaje)
            return redirect('carreras:carreras_list')
        else:
            errores = {campo: [str(e) for e in errs] for campo, errs in form.errors.items()}
            primer_error = next(iter(form.errors.values()))[0] if form.errors else "Error de validación."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                return JsonResponse({'success': False, 'mensaje': str(primer_error), 'errores': errores}, status=400)
            messages.error(request, str(primer_error))

    return JsonResponse({
        'success': True,
        'codigo_carrera': carrera.codigo_carrera,
        'nombre_carrera': carrera.nombre_carrera,
        'resolucion_vigente': carrera.resolucion_vigente or '',
        'resolucion_anterior': carrera.resolucion_anterior or '',
    })


@directivo_required
@csrf_protect
def carrera_eliminar_view(request, codigo_carrera: str):
    """
    Eliminación segura de una carrera y su plan de estudios asociado tras confirmación.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensaje': 'Método no permitido.'}, status=405)

    carrera = get_object_or_404(Carrera, codigo_carrera=codigo_carrera)
    nombre = carrera.nombre_carrera

    try:
        with transaction.atomic():
            carrera.delete()
        mensaje = f"La carrera '{nombre}' y su plan de estudios han sido eliminados correctamente."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'success': True, 'mensaje': mensaje})
        messages.success(request, mensaje)
        return redirect('carreras:carreras_list')
    except Exception as ex:
        err_msg = f"No se pudo eliminar la carrera: {str(ex)}"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'success': False, 'mensaje': err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect('carreras:carreras_list')


@directivo_required
def imprimir_plan_estudio(request, codigo_carrera: str):
    """
    Vista imprimible del plan de estudios oficial de una carrera,
    estructurada con membrete oficial del ISFT N° 188 y materias organizadas por año.
    """
    carrera = get_object_or_404(Carrera, codigo_carrera=codigo_carrera)
    planes = PlanEstudio.objects.filter(carrera=carrera).select_related('materia').order_by('anio_carrera', 'materia__nombre_materia')

    anios_dict: Dict[int, List[PlanEstudio]] = {}
    total_horas_anuales = 0
    total_horas_semanales = Decimal('0.0')

    for p in planes:
        anio = p.anio_carrera or 1
        if anio not in anios_dict:
            anios_dict[anio] = []
        anios_dict[anio].append(p)
        total_horas_anuales += (p.carga_horaria_anual or 0)
        total_horas_semanales += (p.carga_horaria_semanal or Decimal('0.0'))

    anios_lista = []
    for anio in sorted(anios_dict.keys()):
        anios_lista.append({
            'numero': anio,
            'nombre': f"{anio}° Año",
            'planes': anios_dict[anio],
            'total_materias': len(anios_dict[anio]),
        })

    return render(request, 'carreras/imprimir_plan.html', {
        'carrera': carrera,
        'anios': anios_lista,
        'total_materias': planes.count(),
        'total_horas_anuales': total_horas_anuales,
        'total_horas_semanales': total_horas_semanales,
    })


@directivo_required
@csrf_protect
def materia_agregar_carrera(request, codigo_carrera: str):
    """
    Agrega una nueva materia al plan de estudios de la carrera especificada.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensaje': 'Método no permitido.'}, status=405)

    carrera = get_object_or_404(Carrera, codigo_carrera=codigo_carrera)

    codigo_materia = request.POST.get('codigo_materia', '').strip().upper()
    nombre_materia = request.POST.get('nombre_materia', '').strip()
    anio_raw = request.POST.get('anio_carrera', '1').strip()
    modalidad = request.POST.get('modalidad', 'Anual').strip()
    hs_semanales_raw = request.POST.get('carga_horaria_semanal', '0').strip()
    hs_anuales_raw = request.POST.get('carga_horaria_anual', '0').strip()
    correlatividades = request.POST.get('correlatividades', '').strip()

    if not codigo_materia:
        return JsonResponse({'success': False, 'mensaje': 'El código de la materia es obligatorio.'}, status=400)
    if not nombre_materia:
        return JsonResponse({'success': False, 'mensaje': 'El nombre de la materia es obligatorio.'}, status=400)

    try:
        anio_carrera = int(anio_raw)
        if anio_carrera < 1 or anio_carrera > 10:
            anio_carrera = 1
    except ValueError:
        anio_carrera = 1

    try:
        carga_horaria_semanal = Decimal(hs_semanales_raw.replace(',', '.')) if hs_semanales_raw else Decimal('0.0')
    except Exception:
        carga_horaria_semanal = Decimal('0.0')

    semanas = 16 if 'cuatrimestre' in (modalidad or '').lower() else 32
    carga_horaria_anual = int(round(float(carga_horaria_semanal) * semanas))

    if PlanEstudio.objects.filter(carrera=carrera, materia__codigo_materia=codigo_materia).exists():
        return JsonResponse({
            'success': False,
            'mensaje': f"La materia con código '{codigo_materia}' ya existe en el plan de estudios de esta carrera."
        }, status=400)

    try:
        with transaction.atomic():
            materia, created = Materia.objects.get_or_create(
                codigo_materia=codigo_materia,
                defaults={'nombre_materia': nombre_materia}
            )
            if not created and materia.nombre_materia != nombre_materia:
                materia.nombre_materia = nombre_materia
                materia.save()

            plan = PlanEstudio.objects.create(
                carrera=carrera,
                materia=materia,
                anio_carrera=anio_carrera,
                modalidad=modalidad or 'Anual',
                carga_horaria_semanal=carga_horaria_semanal,
                carga_horaria_anual=carga_horaria_anual,
                correlatividades=correlatividades,
            )

        return JsonResponse({
            'success': True,
            'mensaje': f"Materia '{nombre_materia}' incorporada exitosamente al {anio_carrera}° año.",
            'id_plan': plan.id_plan,
        })
    except Exception as ex:
        return JsonResponse({'success': False, 'mensaje': f"Error al agregar materia: {str(ex)}"}, status=400)


@directivo_required
@csrf_protect
def materia_editar_carrera(request, codigo_carrera: str, id_plan: int):
    """
    Edita los datos de una materia dentro del plan de estudios de la carrera.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensaje': 'Método no permitido.'}, status=405)

    carrera = get_object_or_404(Carrera, codigo_carrera=codigo_carrera)
    plan = get_object_or_404(PlanEstudio, id_plan=id_plan, carrera=carrera)

    nombre_materia = request.POST.get('nombre_materia', '').strip()
    anio_raw = request.POST.get('anio_carrera', str(plan.anio_carrera)).strip()
    modalidad = request.POST.get('modalidad', plan.modalidad or 'Anual').strip()
    hs_semanales_raw = request.POST.get('carga_horaria_semanal', str(plan.carga_horaria_semanal or '0')).strip()
    hs_anuales_raw = request.POST.get('carga_horaria_anual', str(plan.carga_horaria_anual or '0')).strip()
    correlatividades = request.POST.get('correlatividades', '').strip()

    if not nombre_materia:
        return JsonResponse({'success': False, 'mensaje': 'El nombre de la materia no puede quedar vacío.'}, status=400)

    try:
        anio_carrera = int(anio_raw)
        if anio_carrera < 1 or anio_carrera > 10:
            anio_carrera = plan.anio_carrera
    except ValueError:
        anio_carrera = plan.anio_carrera

    try:
        carga_horaria_semanal = Decimal(hs_semanales_raw.replace(',', '.')) if hs_semanales_raw else Decimal('0.0')
    except Exception:
        carga_horaria_semanal = plan.carga_horaria_semanal or Decimal('0.0')

    semanas = 16 if 'cuatrimestre' in (modalidad or '').lower() else 32
    carga_horaria_anual = int(round(float(carga_horaria_semanal) * semanas))

    try:
        with transaction.atomic():
            plan.anio_carrera = anio_carrera
            plan.modalidad = modalidad or 'Anual'
            plan.carga_horaria_semanal = carga_horaria_semanal
            plan.carga_horaria_anual = carga_horaria_anual
            plan.correlatividades = correlatividades
            plan.save()

            if plan.materia.nombre_materia != nombre_materia:
                plan.materia.nombre_materia = nombre_materia
                plan.materia.save()

        return JsonResponse({
            'success': True,
            'mensaje': f"Materia '{nombre_materia}' actualizada correctamente.",
            'id_plan': plan.id_plan,
        })
    except Exception as ex:
        return JsonResponse({'success': False, 'mensaje': f"Error al editar materia: {str(ex)}"}, status=400)


@directivo_required
@csrf_protect
def materia_eliminar_carrera(request, codigo_carrera: str, id_plan: int):
    """
    Elimina una materia del plan de estudios de la carrera tras validar que
    no posea cursadas con alumnos ni registros académicos asociados.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensaje': 'Método no permitido.'}, status=405)

    carrera = get_object_or_404(Carrera, codigo_carrera=codigo_carrera)
    plan = get_object_or_404(PlanEstudio, id_plan=id_plan, carrera=carrera)

    # Validar integridad referencial con cursadas de alumnos
    tiene_cursadas = Comision.objects.filter(plan_estudio=plan, cursadas__isnull=False).exists()
    if tiene_cursadas:
        return JsonResponse({
            'success': False,
            'mensaje': f"No se puede eliminar '{plan.materia.nombre_materia}' porque tiene comisiones con cursadas de estudiantes o notas registradas."
        }, status=400)

    try:
        with transaction.atomic():
            nombre_mat = plan.materia.nombre_materia
            Comision.objects.filter(plan_estudio=plan).delete()
            plan.delete()

        return JsonResponse({
            'success': True,
            'mensaje': f"La materia '{nombre_mat}' fue eliminada del plan de estudios exitosamente."
        })
    except Exception as ex:
        return JsonResponse({'success': False, 'mensaje': f"Error al eliminar la materia: {str(ex)}"}, status=400)

