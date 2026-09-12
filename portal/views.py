from collections import defaultdict
from decimal import Decimal
from typing import Dict, Any, List

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_protect

from login.decorators import alumno_required, docente_required
from gestion.models import Alumno, Docente, Cursada, Evaluacion, ComisionDocente
from gestion.views import (
    formatear_dni,
    formatear_cuil,
    formatear_telefono,
)


@alumno_required
@csrf_protect
def portal_alumno_view(request):
    """
    Portal exclusivo para estudiantes.
    Muestra únicamente los datos personales, historial académico ordenado por carrera y año,
    calificaciones parciales y finales, asistencia y docentes a cargo del alumno autenticado.
    """
    dni = str(request.user.username).strip()
    alumno = get_object_or_404(Alumno.objects.select_related('persona'), persona__dni=dni)
    persona = alumno.persona

    cursadas_qs = alumno.cursadas.select_related(
        'comision__plan_estudio__carrera',
        'comision__plan_estudio__materia',
    ).prefetch_related(
        'evaluaciones',
        'comision__docentes_asignados__docente__persona',
    ).all()

    # Agrupar las cursadas por carrera y dentro por año de carrera
    # Estructura: { carrera_key: { 'carrera': Carrera, 'anios': { anio_num: [cursada_data, ...] } } }
    carreras_dict = {}
    notas_totales = []
    asistencias_totales = []
    total_promocionadas = 0
    total_regulares = 0
    total_finales = 0
    total_libres = 0

    for c in cursadas_qs:
        comision = c.comision
        plan = comision.plan_estudio
        carrera = plan.carrera
        materia = plan.materia
        anio = plan.anio_carrera or 1

        carrera_key = carrera.codigo_carrera
        if carrera_key not in carreras_dict:
            carreras_dict[carrera_key] = {
                'carrera': carrera,
                'nombre_carrera': carrera.nombre_carrera,
                'resolucion': carrera.resolucion_vigente or 'Sin resolución',
                'anios': defaultdict(list),
            }

        # Evaluaciones y notas
        evaluaciones = list(c.evaluaciones.all().order_by('fecha', 'codigo_evaluacion'))
        nota_final_obj = None
        evaluaciones_parciales = []

        for ev in evaluaciones:
            if ev.nota is not None:
                notas_totales.append(float(ev.nota))
            inst_lower = (ev.instancia or '').lower()
            if 'final' in inst_lower:
                nota_final_obj = ev
            else:
                evaluaciones_parciales.append(ev)

        # Docentes de la comisión
        docentes_lista = []
        for cd in comision.docentes_asignados.all():
            doc_persona = cd.docente.persona
            docentes_lista.append(f"Prof. {doc_persona.apellido}, {doc_persona.nombre} ({cd.rol})")
        docentes_str = " | ".join(docentes_lista) if docentes_lista else "Docente no asignado"

        # Asistencia
        if c.porcentaje_asistencia is not None:
            asistencias_totales.append(float(c.porcentaje_asistencia))

        # Conteo de situaciones
        if c.situacion_final == 'Promocionado':
            total_promocionadas += 1
        elif c.situacion_final == 'Regular':
            total_regulares += 1
        elif c.situacion_final == 'Final':
            total_finales += 1
        elif c.situacion_final == 'Libre':
            total_libres += 1

        cursada_info = {
            'cursada': c,
            'comision': comision,
            'materia': materia,
            'plan': plan,
            'anio_lectivo': comision.anio_lectivo,
            'turno': comision.turno,
            'division': comision.division,
            'cuatrimestre': comision.cuatrimestre,
            'docentes_str': docentes_str,
            'asistencia': f"{float(c.porcentaje_asistencia):.0f}%" if c.porcentaje_asistencia is not None else "Sin registro",
            'asistencia_val': float(c.porcentaje_asistencia) if c.porcentaje_asistencia is not None else None,
            'situacion': c.situacion_final,
            'evaluaciones_parciales': evaluaciones_parciales,
            'nota_final': nota_final_obj.nota if (nota_final_obj and nota_final_obj.nota is not None) else None,
        }

        carreras_dict[carrera_key]['anios'][anio].append(cursada_info)

    # Convertir a estructura de listas ordenadas para renderizado amigable
    carreras_estructuradas = []
    for c_key, c_data in carreras_dict.items():
        anios_ordenados = []
        for anio_num in sorted(c_data['anios'].keys()):
            anios_ordenados.append({
                'numero': anio_num,
                'titulo': f"{anio_num}° Año",
                'materias': sorted(c_data['anios'][anio_num], key=lambda x: x['materia'].nombre_materia),
            })
        carreras_estructuradas.append({
            'carrera': c_data['carrera'],
            'nombre_carrera': c_data['nombre_carrera'],
            'resolucion': c_data['resolucion'],
            'anios': anios_ordenados,
            'total_materias_carrera': sum(len(a['materias']) for a in anios_ordenados),
        })

    # Estadísticas globales
    promedio_general = round(sum(notas_totales) / len(notas_totales), 2) if notas_totales else None
    asistencia_promedio = round(sum(asistencias_totales) / len(asistencias_totales), 1) if asistencias_totales else None

    context = {
        'alumno': alumno,
        'persona': persona,
        'dni_formateado': formatear_dni(persona.dni),
        'cuil_formateado': formatear_cuil(persona.cuil),
        'telefono_formateado': formatear_telefono(persona.telefono),
        'carreras': carreras_estructuradas,
        'total_materias_cursadas': cursadas_qs.count(),
        'promedio_general': promedio_general,
        'asistencia_promedio': asistencia_promedio,
        'total_promocionadas': total_promocionadas,
        'total_regulares': total_regulares,
        'total_finales': total_finales,
        'total_libres': total_libres,
    }
    return render(request, 'portal/alumno_portal.html', context)


@docente_required
@csrf_protect
def portal_docente_view(request):
    """
    Portal exclusivo para docentes.
    Muestra únicamente los datos personales, profesionales y las asignaturas/comisiones
    en las que el docente se encuentra asignado, organizadas por carrera y año.
    """
    dni = str(request.user.username).strip()
    docente = get_object_or_404(Docente.objects.select_related('persona'), persona__dni=dni)
    persona = docente.persona

    asignaciones_qs = docente.comisiones_asignadas.select_related(
        'comision__plan_estudio__carrera',
        'comision__plan_estudio__materia',
    ).prefetch_related(
        'comision__cursadas',
    ).all()

    # Agrupar comisiones por carrera y año
    carreras_dict = {}
    total_estudiantes = 0
    comisiones_ids = set()

    for asig in asignaciones_qs:
        comision = asig.comision
        plan = comision.plan_estudio
        carrera = plan.carrera
        materia = plan.materia
        anio = plan.anio_carrera or 1

        carrera_key = carrera.codigo_carrera
        if carrera_key not in carreras_dict:
            carreras_dict[carrera_key] = {
                'carrera': carrera,
                'nombre_carrera': carrera.nombre_carrera,
                'resolucion': carrera.resolucion_vigente or 'Sin resolución',
                'anios': defaultdict(list),
            }

        cant_alumnos = comision.cursadas.count()
        total_estudiantes += cant_alumnos
        comisiones_ids.add(comision.codigo_comision)

        item = {
            'materia': materia,
            'plan': plan,
            'comision': comision,
            'rol': asig.rol,
            'anio_lectivo': comision.anio_lectivo,
            'turno': comision.turno,
            'division': comision.division,
            'cuatrimestre': comision.cuatrimestre,
            'hs_semanales': plan.carga_horaria_semanal,
            'hs_anuales': plan.carga_horaria_anual,
            'cantidad_estudiantes': cant_alumnos,
        }
        carreras_dict[carrera_key]['anios'][anio].append(item)

    # Convertir a estructura ordenada
    carreras_estructuradas = []
    for c_key, c_data in carreras_dict.items():
        anios_ordenados = []
        for anio_num in sorted(c_data['anios'].keys()):
            anios_ordenados.append({
                'numero': anio_num,
                'titulo': f"{anio_num}° Año",
                'comisiones': sorted(c_data['anios'][anio_num], key=lambda x: x['materia'].nombre_materia),
            })
        carreras_estructuradas.append({
            'carrera': c_data['carrera'],
            'nombre_carrera': c_data['nombre_carrera'],
            'resolucion': c_data['resolucion'],
            'anios': anios_ordenados,
            'total_comisiones_carrera': sum(len(a['comisiones']) for a in anios_ordenados),
        })

    context = {
        'docente': docente,
        'persona': persona,
        'dni_formateado': formatear_dni(persona.dni),
        'cuil_formateado': formatear_cuil(persona.cuil),
        'telefono_formateado': formatear_telefono(persona.telefono),
        'carreras': carreras_estructuradas,
        'total_asignaturas': len({asig.comision.plan_estudio.materia.codigo_materia for asig in asignaciones_qs}),
        'total_comisiones': len(comisiones_ids),
        'total_estudiantes': total_estudiantes,
    }
    return render(request, 'portal/docente_portal.html', context)
