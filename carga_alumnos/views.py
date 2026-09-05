import datetime
from typing import Any, Dict, List, Optional
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.apps import apps
from .models import Alumno
from .forms import AlumnoForm

SESSION_KEY = 'carga_alumnos_temp_data_list'


def get_alumnos_sesion(request: Any) -> List[Dict[str, Any]]:
    """
    Recupera la lista de alumnos acumulados en la sesión para la carga en matriz.
    Mantiene compatibilidad hacia atrás si la sesión contenía un diccionario individual.
    """
    data = request.session.get(SESSION_KEY, [])
    if isinstance(data, dict):
        return [data] if data else []
    if isinstance(data, list):
        return data
    return []


@login_required(login_url='login:login')
def index(request: Any) -> Any:
    """
    Redirige de forma directa al formulario de carga de alumnos (Paso 1).
    """
    return redirect(reverse('carga_alumnos:paso1_carga'))


@login_required(login_url='login:login')
def paso1_carga(request: Any) -> Any:
    """
    Paso 1: Formulario directo de ingreso secuencial y validado de datos del alumno.
    Permite cargar un alumno o acumular múltiples alumnos en la matriz de la sesión.
    """
    alumnos_acumulados = get_alumnos_sesion(request)

    if request.method == 'POST':
        form = AlumnoForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data.copy()

            # Formatear la fecha como string ISO para serialización en sesión
            fecha_val = cleaned.get('fecha_nacimiento')
            if isinstance(fecha_val, (datetime.date, datetime.datetime)):
                cleaned['fecha_nacimiento'] = fecha_val.strftime('%Y-%m-%d')

            dni_nuevo = cleaned.get('dni')
            cuil_nuevo = cleaned.get('cuil')

            # Validar que no se repita en la tanda actual de la sesión
            if any(a.get('dni') == dni_nuevo for a in alumnos_acumulados):
                messages.error(request, f"El alumno con DNI {dni_nuevo} ya fue ingresado en esta tanda de carga.")
                return render(request, 'carga_alumnos/paso1_carga.html', {
                    'form': form,
                    'total_en_matriz': len(alumnos_acumulados),
                    'hay_borrador_pendiente': bool(alumnos_acumulados),
                })

            if any(a.get('cuil') == cuil_nuevo for a in alumnos_acumulados):
                messages.error(request, f"El alumno con CUIL {cuil_nuevo} ya fue ingresado en esta tanda de carga.")
                return render(request, 'carga_alumnos/paso1_carga.html', {
                    'form': form,
                    'total_en_matriz': len(alumnos_acumulados),
                    'hay_borrador_pendiente': bool(alumnos_acumulados),
                })

            # Agregar a la lista de la matriz en sesión
            alumnos_acumulados.append(cleaned)
            request.session[SESSION_KEY] = alumnos_acumulados
            request.session.modified = True

            messages.success(
                request,
                f"Alumno {cleaned.get('apellido')}, {cleaned.get('nombre')} incorporado a la matriz de verificación."
            )
            return redirect(reverse('carga_alumnos:paso2_confirmacion'))
        else:
            cant_errores = len(form.errors)
            campos_con_error = [field.label for field in form if field.errors]
            if cant_errores == 1 and campos_con_error:
                resumen = f"Se detectó 1 error en '{campos_con_error[0]}'. Por favor revise el detalle señalado en rojo."
            elif campos_con_error:
                lista_nombres = ", ".join(campos_con_error[:3])
                if len(campos_con_error) > 3:
                    lista_nombres += f" y {len(campos_con_error) - 3} más"
                resumen = f"Se detectaron {cant_errores} errores en el formulario ({lista_nombres}). Corrija los campos señalados en rojo a continuación."
            else:
                resumen = f"Se detectaron {cant_errores} inconsistencias en el formulario. Por favor revise el detalle señalado en rojo."

            messages.error(request, resumen)
    else:
        # En GET: Si hay datos para edición, cargarlos en el formulario
        datos_edit = request.session.pop('carga_alumnos_edit_data', None)
        if datos_edit:
            request.session.modified = True
            form = AlumnoForm(initial=datos_edit)
        else:
            form = AlumnoForm()

    context: Dict[str, Any] = {
        'form': form,
        'total_en_matriz': len(alumnos_acumulados),
        'hay_borrador_pendiente': bool(alumnos_acumulados),
    }
    return render(request, 'carga_alumnos/paso1_carga.html', context)


@login_required(login_url='login:login')
def paso2_confirmacion(request: Any) -> Any:
    """
    Paso 2: Previsualización en matriz de datos completa y confirmación.
    Permite visualizar uno o más alumnos en una matriz completa sin desplazamiento horizontal.
    - 'confirmar': guarda todos los alumnos de la matriz en base de datos y sincroniza con gestión.
    - 'nuevo_alumno': conserva la matriz actual y abre el Paso 1 para sumar otro alumno.
    - 'modificar': extrae el último alumno para corregirlo en el Paso 1.
    - 'editar_fila': extrae un alumno específico según índice para corregirlo en el Paso 1.
    - 'eliminar_fila': quita un alumno específico de la matriz antes de confirmar.
    - 'cancelar': descarta toda la matriz y reinicia la carga.
    """
    alumnos_lista = get_alumnos_sesion(request)

    # Si no existen alumnos en la matriz, redirigir al paso 1
    if not alumnos_lista:
        messages.warning(request, "No hay ningún alumno en la matriz de carga. Ingrese los datos primero.")
        return redirect(reverse('carga_alumnos:paso1_carga'))

    # Mapeo de género humano para la presentación
    genero_dict = dict(Alumno.GENERO_CHOICES)
    alumnos_matriz: List[Dict[str, Any]] = []
    for idx, item in enumerate(alumnos_lista):
        copia = item.copy()
        copia['fila_num'] = idx + 1
        copia['fila_index'] = idx
        copia['genero_humano'] = genero_dict.get(item.get('genero', ''), item.get('genero', ''))
        alumnos_matriz.append(copia)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'confirmar':
            guardados_ok = 0
            errores = []

            for datos in alumnos_lista:
                dni_candidato = str(datos.get('dni', '')).strip()
                cuil_candidato = str(datos.get('cuil', '')).strip()

                # Validar duplicados en base de datos
                if Alumno.objects.filter(dni=dni_candidato).exists():
                    errores.append(f"DNI {dni_candidato} ya existe en base de datos.")
                    continue
                if Alumno.objects.filter(cuil=cuil_candidato).exists():
                    errores.append(f"CUIL {cuil_candidato} ya existe en base de datos.")
                    continue

                try:
                    fecha_str = str(datos.get('fecha_nacimiento', ''))
                    fecha_obj = datetime.datetime.strptime(fecha_str, '%Y-%m-%d').date()

                    nuevo_alumno = Alumno(
                        dni=dni_candidato,
                        cuil=cuil_candidato,
                        nombre=str(datos.get('nombre', '')),
                        apellido=str(datos.get('apellido', '')),
                        fecha_nacimiento=fecha_obj,
                        email=str(datos.get('email', '')),
                        telefono=str(datos.get('telefono', '')),
                        direccion=str(datos.get('direccion', '')),
                        localidad=str(datos.get('localidad', 'General Rodríguez')),
                        genero=str(datos.get('genero', 'N')),
                        nacionalidad=str(datos.get('nacionalidad', 'Argentina')),
                    )
                    nuevo_alumno.save()

                    # Sincronización modular con el módulo central gestion
                    try:
                        if apps.is_installed('gestion'):
                            PersonaModel = apps.get_model('gestion', 'Persona')
                            AlumnoGestionModel = apps.get_model('gestion', 'Alumno')

                            persona, _ = PersonaModel.objects.update_or_create(
                                dni=dni_candidato,
                                defaults={
                                    'cuil': cuil_candidato,
                                    'nombre': nuevo_alumno.nombre,
                                    'apellido': nuevo_alumno.apellido,
                                    'domicilio': nuevo_alumno.direccion,
                                    'localidad': nuevo_alumno.localidad,
                                    'telefono': nuevo_alumno.telefono,
                                    'mail': nuevo_alumno.email,
                                    'nacionalidad': nuevo_alumno.nacionalidad,
                                    'fecha_nacimiento': nuevo_alumno.fecha_nacimiento,
                                    'identidad': nuevo_alumno.genero,
                                }
                            )
                            AlumnoGestionModel.objects.get_or_create(
                                persona=persona,
                                defaults={'legajo': f"LEG-{dni_candidato}"}
                            )
                    except Exception:
                        pass

                    guardados_ok += 1

                except Exception as e:
                    errores.append(f"Error con DNI {dni_candidato}: {e}")

            # Limpiar la sesión
            if SESSION_KEY in request.session:
                del request.session[SESSION_KEY]
                request.session.modified = True

            if guardados_ok > 0:
                messages.success(
                    request,
                    f"¡Excelente! Se han guardado exitosamente {guardados_ok} alumno(s) en el sistema."
                )
            if errores:
                for err in errores:
                    messages.error(request, err)

            return redirect(reverse('carga_alumnos:paso1_carga'))

        elif accion == 'nuevo_alumno':
            # Abre el paso 1 conservando los ya cargados para añadir otro alumno a la matriz
            messages.info(request, "Completá el formulario para sumar otro alumno a la matriz.")
            return redirect(reverse('carga_alumnos:paso1_carga'))

        elif accion == 'modificar':
            if alumnos_lista:
                datos_edit = alumnos_lista.pop()
                request.session[SESSION_KEY] = alumnos_lista
                request.session['carga_alumnos_edit_data'] = datos_edit
                request.session.modified = True
                messages.info(request, f"Modificando datos de {datos_edit.get('apellido', '')}, {datos_edit.get('nombre', '')}.")
            return redirect(reverse('carga_alumnos:paso1_carga'))

        elif accion == 'editar_fila':
            try:
                fila_idx = int(request.POST.get('fila_index', -1))
                if 0 <= fila_idx < len(alumnos_lista):
                    datos_edit = alumnos_lista.pop(fila_idx)
                    request.session[SESSION_KEY] = alumnos_lista
                    request.session['carga_alumnos_edit_data'] = datos_edit
                    request.session.modified = True
                    messages.info(request, f"Modificando datos de {datos_edit.get('apellido', '')}, {datos_edit.get('nombre', '')}.")
                    return redirect(reverse('carga_alumnos:paso1_carga'))
            except (ValueError, TypeError):
                pass
            return redirect(reverse('carga_alumnos:paso2_confirmacion'))

        elif accion == 'eliminar_fila':
            try:
                fila_idx = int(request.POST.get('fila_index', -1))
                if 0 <= fila_idx < len(alumnos_lista):
                    eliminado = alumnos_lista.pop(fila_idx)
                    request.session[SESSION_KEY] = alumnos_lista
                    request.session.modified = True
                    messages.info(request, f"Se quitó a {eliminado.get('apellido', '')}, {eliminado.get('nombre', '')} de la matriz.")
            except (ValueError, TypeError):
                pass

            if not alumnos_lista:
                return redirect(reverse('carga_alumnos:paso1_carga'))
            return redirect(reverse('carga_alumnos:paso2_confirmacion'))

        elif accion == 'cancelar':
            # Descartar toda la matriz
            if SESSION_KEY in request.session:
                del request.session[SESSION_KEY]
                request.session.modified = True

            messages.info(request, "Carga cancelada. La matriz de alumnos ha sido vaciada.")
            return redirect(reverse('carga_alumnos:paso1_carga'))

    context: Dict[str, Any] = {
        'alumnos_matriz': alumnos_matriz,
        'total_alumnos': len(alumnos_matriz),
    }
    return render(request, 'carga_alumnos/paso2_confirmacion.html', context)
