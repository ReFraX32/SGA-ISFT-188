import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import io
import datetime
import re
from django.db import transaction
from gestion.models import Persona, Alumno, Carrera, Materia, PlanEstudio, Comision, Cursada

def fix_accents(text):
    if not text:
        return text
    replacements = {
        'à': 'á', 'è': 'é', 'ì': 'í', 'ò': 'ó', 'ù': 'ú',
        'À': 'Á', 'È': 'É', 'Ì': 'Í', 'Ò': 'Ó', 'Ù': 'Ú',
        'â': 'á', 'ê': 'é', 'î': 'í', 'ô': 'ó', 'û': 'ú',
        'Â': 'Á', 'Ê': 'É', 'Î': 'Í', 'Ô': 'Ó', 'Û': 'Ú',
        'ã': 'a', 'õ': 'o', 'Ã': 'A', 'Õ': 'O',
    }
    s = str(text)
    for bad, good in replacements.items():
        s = s.replace(bad, good)
    return s

def clean_title_case(text):
    if not text or str(text).strip() in ['', 'None', '-', 'nan', 'S/D', 'S/N', 'S/A']:
        return ""
    text = fix_accents(str(text).strip())
    lower_connectors = {'de', 'del', 'la', 'las', 'el', 'los', 'y', 'e', 'da', 'di', 'do', 'das', 'dos', 'van', 'von', 'd'}
    words = text.split()
    result = []
    for i, w in enumerate(words):
        if '-' in w:
            subwords = [sw.capitalize() for sw in w.split('-')]
            w_cap = '-'.join(subwords)
        elif "'" in w:
            subwords = [sw.capitalize() for sw in w.split("'")]
            w_cap = "'".join(subwords)
        else:
            w_lower = w.lower()
            if i > 0 and w_lower in lower_connectors:
                w_cap = w_lower
            else:
                w_cap = w.capitalize()
        result.append(w_cap)
    return " ".join(result)

def clean_gender(val):
    if not val:
        return 'N'
    v = str(val).strip().lower()
    gender_map = {
        'masculino': 'M', 'm': 'M', 'varon': 'M', 'varón': 'M', 'hombre': 'M',
        'femenino': 'F', 'f': 'F', 'mujer': 'F',
        'otro': 'O', 'no binario': 'O', 'nobinario': 'O', 'o': 'O',
        'prefiere no decir': 'N', 'prefiero no decir': 'N', 'n': 'N', 'none': 'N'
    }
    return gender_map.get(v, 'N')

def parse_date(val):
    if not val or str(val).strip() in ['', 'None', '-', '--']:
        return None
    if isinstance(val, datetime.datetime):
        return val.date()
    if isinstance(val, datetime.date):
        return val
    s = str(val).strip().split(' ')[0]
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d'):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None

def clean_phone(val):
    if not val or str(val).strip() in ['', 'None', '-']:
        return None
    s = str(val).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s

def clean_cuil(val):
    if not val or str(val).strip() in ['', 'None', '-']:
        return None
    s = str(val).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s.replace('-', '').replace('.', '').replace(' ', '')

def clean_dni(val):
    if not val:
        return None
    s = str(val).strip()
    if s.endswith('.0'):
        s = s[:-2]
    # Extraer dígitos
    digits = re.sub(r'\D', '', s)
    return digits if len(digits) >= 6 and len(digits) <= 10 else None

def generar_plantilla_alumnos_excel():
    """
    Genera un archivo Excel oficial (.xlsx) diseñado específicamente para directivos
    con instrucciones claras, validaciones y formato intuitivo para la carga de alumnos.
    """
    wb = openpyxl.Workbook()
    
    # ----------------------------------------------------
    # HOJA 1: CARGA DE ALUMNOS
    # ----------------------------------------------------
    ws = wb.active
    ws.title = "Carga de Alumnos"
    ws.views.sheetView[0].showGridLines = True

    # Estilos
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    sample_font = Font(name="Arial", size=9, italic=True, color="475569")
    data_font = Font(name="Arial", size=10, color="0F172A")
    inst_font = Font(name="Arial", size=9, bold=True, color="1E3A8A")
    inst_fill = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
    
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    # Título institucional
    ws.merge_cells("A1:M1")
    t_cell = ws["A1"]
    t_cell.value = "INSTITUTO SUPERIOR DE FORMACIÓN TÉCNICA N° 188 — PLANTILLA OFICIAL DE CARGA DE ALUMNOS"
    t_cell.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    t_cell.fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    t_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # Fila de Instrucciones
    ws.merge_cells("A2:M2")
    i_cell = ws["A2"]
    i_cell.value = "📌 INSTRUCCIONES: Complete una fila por alumno. DNI, Apellido y Nombre son obligatorios. Los demás campos son opcionales (si no cuenta con el dato, déjelo vacío)."
    i_cell.font = inst_font
    i_cell.fill = inst_fill
    i_cell.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[2].height = 24

    # Encabezados de Columnas
    headers = [
        ("DNI (*)", "Obligatorio (ej: 45039996 o 45.039.996)"),
        ("Apellido (*)", "Obligatorio (ej: Gómez, Pérez)"),
        ("Nombre (*)", "Obligatorio (ej: Juan Carlos)"),
        ("Carrera", "Nombre o Código de la Tecnicatura (ej: Energía, Higiene, Logística)"),
        ("Año de Cursada", "1, 2 o 3 (Año lectivo en la carrera)"),
        ("CUIL", "Opcional (ej: 20450399966)"),
        ("Fecha de Nacimiento", "Opcional (Formato DD/MM/AAAA ej: 15/04/2001)"),
        ("Identidad de Género", "Opcional (Masculino, Femenino, Otro, Prefiere no decir)"),
        ("Nacionalidad", "Opcional (por defecto Argentina)"),
        ("Localidad", "Opcional (ej: General Rodríguez, Moreno, Luján)"),
        ("Domicilio", "Opcional (ej: Av. España 1234)"),
        ("Teléfono / Celular", "Opcional (ej: 1123456789)"),
        ("Correo Electrónico", "Opcional (ej: alumno@gmail.com — si no tiene déjelo vacío)")
    ]

    ws.row_dimensions[3].height = 28
    for col_idx, (h_title, comment_txt) in enumerate(headers, start=1):
        cell = ws.cell(3, col_idx)
        cell.value = h_title
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    # Filas de Ejemplo (con texto de muestra)
    ejemplos = [
        ("45039996", "Abeldaño Aquino", "Gonzalo Daniel", "Tecnicatura Superior en Energía", "1", "20450399966", "13/01/2000", "Masculino", "Argentina", "Moreno", "Angel Gallardo 6160", "1130858866", "gonzalodaniel2107@gmail.com"),
        ("39110038", "Alegre", "Aldana Micaela", "Tecnicatura Superior en Higiene", "2", "27391100384", "18/09/1995", "Femenino", "Argentina", "General Rodríguez", "México Manzana 3 Casa 41", "1155443322", ""),
        ("34412371", "Acosta", "María Noemí", "Tecnicatura Superior en Logística", "1", "", "", "Prefiere no decir", "Argentina", "General Rodríguez", "", "", "")
    ]

    for r_idx, ej in enumerate(ejemplos, start=4):
        ws.row_dimensions[r_idx].height = 20
        for c_idx, val in enumerate(ej, start=1):
            cell = ws.cell(r_idx, c_idx)
            cell.value = val
            cell.font = sample_font
            cell.alignment = Alignment(horizontal="left" if c_idx in [2, 3, 4, 10, 11, 13] else "center", vertical="center")
            cell.border = thin_border
            cell.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    # Filas en blanco para que el usuario complete (filas 7 a 50)
    for r in range(7, 40):
        ws.row_dimensions[r].height = 20
        for c in range(1, len(headers) + 1):
            cell = ws.cell(r, c)
            cell.font = data_font
            cell.alignment = Alignment(horizontal="left" if c in [2, 3, 4, 10, 11, 13] else "center", vertical="center")
            cell.border = thin_border

    # Ajuste automático de anchos de columna
    col_widths = [16, 22, 24, 32, 16, 18, 20, 20, 16, 20, 28, 18, 30]
    for i, w in enumerate(col_widths, start=1):
        col_letter = get_column_letter(i)
        ws.column_dimensions[col_letter].width = w

    # ----------------------------------------------------
    # HOJA 2: GUÍA DE CARRERAS DISPONIBLES
    # ----------------------------------------------------
    ws_info = wb.create_sheet(title="Carreras Disponibles")
    ws_info.views.sheetView[0].showGridLines = True
    
    ws_info.merge_cells("A1:C1")
    c_title = ws_info["A1"]
    c_title.value = "CATÁLOGO DE CARRERAS Y TECNICATURAS HABILITADAS (ISFT N° 188)"
    c_title.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    c_title.fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    c_title.alignment = Alignment(horizontal="center", vertical="center")
    ws_info.row_dimensions[1].height = 26

    ws_info.cell(2, 1, "Código").font = header_font
    ws_info.cell(2, 1).fill = header_fill
    ws_info.cell(2, 2, "Nombre Oficial de la Carrera").font = header_font
    ws_info.cell(2, 2).fill = header_fill
    ws_info.cell(2, 3, "Resolución").font = header_font
    ws_info.cell(2, 3).fill = header_fill
    ws_info.row_dimensions[2].height = 22

    carreras_db = Carrera.objects.all().order_by('nombre_carrera')
    for row_idx, c in enumerate(carreras_db, start=3):
        ws_info.row_dimensions[row_idx].height = 19
        ws_info.cell(row_idx, 1, c.codigo_carrera).font = data_font
        ws_info.cell(row_idx, 2, c.nombre_carrera).font = data_font
        ws_info.cell(row_idx, 3, c.resolucion_vigente).font = data_font
        for col_idx in (1, 2, 3):
            ws_info.cell(row_idx, col_idx).border = thin_border
            if row_idx % 2 == 0:
                ws_info.cell(row_idx, col_idx).fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    ws_info.column_dimensions['A'].width = 22
    ws_info.column_dimensions['B'].width = 65
    ws_info.column_dimensions['C'].width = 18

    # Guardar en buffer de bytes
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

@transaction.atomic
def procesar_importacion_alumnos_excel(file_obj):
    """
    Procesa un archivo Excel subido por el usuario para registrar/actualizar alumnos.
    Es tolerante a campos vacíos, variaciones de encabezados y detecta inconsistencias.
    """
    summary = {
        'success': False,
        'creados': 0,
        'actualizados': 0,
        'filas_procesadas': 0,
        'errores': [],
        'advertencias': [],
        'mensaje': ''
    }

    try:
        wb = openpyxl.load_workbook(file_obj, data_only=True)
    except Exception as e:
        summary['mensaje'] = f"El archivo proporcionado no es un archivo Excel (.xlsx) válido: {str(e)}"
        return summary

    ws = None
    for sheet_name in ["Carga de Alumnos", "Alumnos", "Hoja 1", "Sheet1"]:
        if sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            break
    if not ws:
        ws = wb.active

    if not ws or ws.max_row < 2:
        summary['mensaje'] = "La hoja de cálculo no contiene filas suficientes de datos para procesar."
        return summary

    # Detectar fila de encabezados buscando 'DNI' o 'DOCUMENTO'
    header_row = None
    col_map = {}
    for r in range(1, min(10, ws.max_row + 1)):
        row_vals = [str(ws.cell(r, c).value or "").strip().upper() for c in range(1, ws.max_column + 1)]
        if any("DNI" in v or "DOCUMENTO" in v for v in row_vals):
            header_row = r
            for c_idx, val in enumerate(row_vals, 1):
                if "DNI" in val or "DOCUMENTO" in val: col_map["dni"] = c_idx
                elif "APELLIDO" in val: col_map["apellido"] = c_idx
                elif "NOMBRE" in val and "CARRERA" not in val: col_map["nombre"] = c_idx
                elif "CARRERA" in val or "TECNICATURA" in val: col_map["carrera"] = c_idx
                elif "AÑO" in val or "ANIO" in val or "CURSADA" in val: col_map["anio"] = c_idx
                elif "CUIL" in val: col_map["cuil"] = c_idx
                elif "FECHA" in val or "NACIMIENTO" in val: col_map["fecha_nac"] = c_idx
                elif "GENERO" in val or "GÉNERO" in val or "IDENTIDAD" in val: col_map["genero"] = c_idx
                elif "NACIONALIDAD" in val: col_map["nacionalidad"] = c_idx
                elif "LOCALIDAD" in val or "CIUDAD" in val: col_map["localidad"] = c_idx
                elif "DOMICILIO" in val or "DIRECCION" in val or "DIRECCIÓN" in val: col_map["domicilio"] = c_idx
                elif "CELULAR" in val or "TELEFONO" in val or "TELÉFONO" in val: col_map["telefono"] = c_idx
                elif "CORREO" in val or "EMAIL" in val or "MAIL" in val: col_map["mail"] = c_idx
                elif "LEGAJO" in val: col_map["legajo"] = c_idx
            break

    if not header_row or "dni" not in col_map:
        summary['mensaje'] = "No se encontró la columna obligatoria 'DNI' en los encabezados del Excel."
        return summary

    # Cache de carreras para vinculación rápida
    carreras_disponibles = list(Carrera.objects.all())

    # Procesar filas de datos
    for r in range(header_row + 1, ws.max_row + 1):
        dni_val = ws.cell(r, col_map["dni"]).value
        if not dni_val or str(dni_val).strip() in ["", "None", "TOTAL"]:
            continue

        dni_str = str(dni_val).strip()
        # Ignorar si es una fila de ejemplo con datos conocidos de muestra
        if r in [4, 5, 6] and dni_str in ["45039996", "39110038", "34412371"] and "ejemplo" in str(ws.cell(2, 1).value or "").lower():
            # Si el usuario dejó la plantilla intacta con los 3 ejemplos, verificar si no hay más filas
            pass

        dni_clean = clean_dni(dni_val)
        if not dni_clean:
            summary['errores'].append(f"Fila {r}: El DNI '{dni_val}' no tiene un formato numérico válido.")
            continue

        ap_raw = ws.cell(r, col_map.get("apellido", 2)).value if "apellido" in col_map else ""
        nom_raw = ws.cell(r, col_map.get("nombre", 3)).value if "nombre" in col_map else ""
        
        ap_clean = clean_title_case(ap_raw)
        nom_clean = clean_title_case(nom_raw)

        if not ap_clean and not nom_clean:
            summary['errores'].append(f"Fila {r} (DNI {dni_clean}): Se requiere ingresar al menos el Apellido o Nombre del estudiante.")
            continue

        if not ap_clean: ap_clean = "S/A"
        if not nom_clean: nom_clean = "S/N"

        # Campos Opcionales
        carrera_raw = str(ws.cell(r, col_map.get("carrera", 4)).value or "").strip() if "carrera" in col_map else ""
        anio_raw = ws.cell(r, col_map.get("anio", 5)).value if "anio" in col_map else None
        cuil_raw = ws.cell(r, col_map.get("cuil", 6)).value if "cuil" in col_map else None
        fnac_raw = ws.cell(r, col_map.get("fecha_nac", 7)).value if "fecha_nac" in col_map else None
        gen_raw = ws.cell(r, col_map.get("genero", 8)).value if "genero" in col_map else None
        nac_raw = str(ws.cell(r, col_map.get("nacionalidad", 9)).value or "").strip() if "nacionalidad" in col_map else ""
        loc_raw = str(ws.cell(r, col_map.get("localidad", 10)).value or "").strip() if "localidad" in col_map else ""
        dom_raw = str(ws.cell(r, col_map.get("domicilio", 11)).value or "").strip() if "domicilio" in col_map else ""
        tel_raw = ws.cell(r, col_map.get("telefono", 12)).value if "telefono" in col_map else None
        mail_raw = str(ws.cell(r, col_map.get("mail", 13)).value or "").strip() if "mail" in col_map else ""
        legajo_raw = str(ws.cell(r, col_map.get("legajo", 14)).value or "").strip() if "legajo" in col_map else ""

        cuil_clean = clean_cuil(cuil_raw)
        fnac_clean = parse_date(fnac_raw)
        gen_sigla = clean_gender(gen_raw)
        nacionalidad_clean = clean_title_case(nac_raw) if nac_raw and nac_raw != 'None' else 'Argentina'
        localidad_clean = clean_title_case(loc_raw) if loc_raw and loc_raw != 'None' else None
        domicilio_clean = fix_accents(dom_raw) if dom_raw and dom_raw != 'None' else None
        tel_clean = clean_phone(tel_raw)
        
        # Validar correo: solo guardar si tiene @ y formato válido, nunca inventar
        mail_clean = mail_raw if mail_raw and '@' in mail_raw and not mail_raw.endswith('@isft188.edu.ar') and mail_raw != 'None' else None

        # Guardar / Actualizar Persona
        persona_obj, created = Persona.objects.get_or_create(
            dni=dni_clean,
            defaults={
                'nombre': nom_clean,
                'apellido': ap_clean,
                'cuil': cuil_clean,
                'fecha_nacimiento': fnac_clean,
                'identidad': gen_sigla,
                'nacionalidad': nacionalidad_clean,
                'localidad': localidad_clean,
                'domicilio': domicilio_clean,
                'telefono': tel_clean,
                'mail': mail_clean
            }
        )

        if not created:
            # Actualizar campos no vacíos
            if nom_clean and persona_obj.nombre != nom_clean: persona_obj.nombre = nom_clean
            if ap_clean and persona_obj.apellido != ap_clean: persona_obj.apellido = ap_clean
            if cuil_clean and not persona_obj.cuil: persona_obj.cuil = cuil_clean
            if fnac_clean and not persona_obj.fecha_nacimiento: persona_obj.fecha_nacimiento = fnac_clean
            if gen_sigla != 'N' and persona_obj.identidad == 'N': persona_obj.identidad = gen_sigla
            if localidad_clean and not persona_obj.localidad: persona_obj.localidad = localidad_clean
            if domicilio_clean and not persona_obj.domicilio: persona_obj.domicilio = domicilio_clean
            if tel_clean and not persona_obj.telefono: persona_obj.telefono = tel_clean
            if mail_clean and not persona_obj.mail: persona_obj.mail = mail_clean
            persona_obj.save()
            summary['actualizados'] += 1
        else:
            summary['creados'] += 1

        # Crear o actualizar Alumno
        legajo_final = legajo_raw if legajo_raw and legajo_raw != 'None' else f"LEG-{dni_clean}"
        alumno_obj, _ = Alumno.objects.get_or_create(
            persona=persona_obj,
            defaults={'legajo': legajo_final}
        )

        # Vincular Cursada si se especificó Carrera y Año
        if carrera_raw and carrera_raw != 'None':
            carrera_match = None
            c_raw_clean = fix_accents(carrera_raw).lower()
            for c_cand in carreras_disponibles:
                if c_cand.codigo_carrera.lower() in c_raw_clean or c_raw_clean in c_cand.nombre_carrera.lower() or c_cand.nombre_carrera.lower() in c_raw_clean:
                    carrera_match = c_cand
                    break

            if carrera_match:
                try:
                    anio_num = int(str(anio_raw).replace('°', '').replace('º', '').strip()) if anio_raw else 1
                except (ValueError, TypeError):
                    anio_num = 1
                
                planes = PlanEstudio.objects.filter(carrera=carrera_match, anio_carrera=anio_num)
                if not planes.exists():
                    planes = PlanEstudio.objects.filter(carrera=carrera_match)
                
                for plan in planes:
                    com = Comision.objects.filter(plan_estudio=plan).first()
                    if not com:
                        com, _ = Comision.objects.get_or_create(
                            codigo_comision=f"COM_{plan.id_plan}_2026",
                            defaults={'plan_estudio': plan, 'anio_lectivo': 2026}
                        )
                    Cursada.objects.get_or_create(
                        comision=com,
                        alumno=alumno_obj,
                        defaults={'situacion_final': 'Regular', 'porcentaje_asistencia': 80.0}
                    )
            else:
                summary['advertencias'].append(f"Fila {r} (DNI {dni_clean}): La carrera '{carrera_raw}' no coincidió con ninguna carrera registrada, por lo que el alumno se registró sin cursada automática.")

        summary['filas_procesadas'] += 1

    summary['success'] = True
    summary['mensaje'] = f"Importación finalizada con éxito: {summary['creados']} alumnos nuevos registrados y {summary['actualizados']} alumnos actualizados."
    return summary
