import datetime
import io
import openpyxl
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from gestion.models import Persona, Alumno, Docente, Carrera, Materia, PlanEstudio, Comision, ComisionDocente, Cursada, Evaluacion
from gestion.views import formatear_carreras_con_resolucion

class BuscadorAlumnosTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Usuario autenticado para pruebas
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username='admin',
            password='mde123'
        )
        self.client.login(username='admin', password='mde123')

        # Alumno 1: Masculino con correo
        self.persona1 = Persona.objects.create(
            dni="45039996",
            cuil="20450399966",
            nombre="Gonzalo Daniel",
            apellido="Abeldaño Aquino",
            domicilio="Angel Gallardo 6160",
            localidad="Moreno",
            telefono="+5492975060752",
            mail="gonzalodaniel2107@gmail.com",
            nacionalidad="Argentina",
            fecha_nacimiento=datetime.date(2000, 1, 13),
            identidad="M"
        )
        self.alumno1 = Alumno.objects.create(
            persona=self.persona1,
            legajo="LEG-45039996"
        )

        # Alumno 2: Femenino sin correo
        self.persona2 = Persona.objects.create(
            dni="39110038",
            cuil="27391100384",
            nombre="Aldana Micaela",
            apellido="Alegre",
            domicilio="México Manzana 3 Casa 41",
            localidad="General Rodríguez",
            telefono="+5491130858866",
            mail=None,
            nacionalidad="Argentina",
            fecha_nacimiento=datetime.date(1995, 9, 18),
            identidad="F"
        )
        self.alumno2 = Alumno.objects.create(
            persona=self.persona2,
            legajo="LEG-39110038"
        )

        # Alumno 3: Indistinto con otra nacionalidad
        self.persona3 = Persona.objects.create(
            dni="41000000",
            cuil="20410000006",
            nombre="Sam",
            apellido="Frette",
            domicilio="Belgrano 134",
            localidad="Jáuregui",
            telefono="+5492323359296",
            mail="sam.frette@gmail.com",
            nacionalidad="Uruguaya",
            fecha_nacimiento=datetime.date(2001, 12, 2),
            identidad="I"
        )
        self.alumno3 = Alumno.objects.create(
            persona=self.persona3,
            legajo="LEG-41000000"
        )

        # Carrera 1 (Res. 320/13) y Materias
        self.carrera = Carrera.objects.create(
            codigo_carrera="HIGIENE-320",
            nombre_carrera="Tecnicatura Superior en Higiene y Seguridad en el Trabajo",
            resolucion_vigente="Res. 320/13"
        )
        self.materia1 = Materia.objects.create(
            codigo_materia="HIGIENE_1",
            nombre_materia="Administración de las organizaciones"
        )
        self.plan1 = PlanEstudio.objects.create(
            carrera=self.carrera,
            materia=self.materia1,
            anio_carrera=1,
            carga_horaria_anual=96,
            carga_horaria_semanal=3
        )
        self.comision1 = Comision.objects.create(
            codigo_comision="COM_HIG_1_2026",
            plan_estudio=self.plan1,
            anio_lectivo=2026
        )

        # Carrera 2 (Misma carrera, distinta resolución: Res. 6183/25)
        self.carrera2 = Carrera.objects.create(
            codigo_carrera="HIGIENE-6183",
            nombre_carrera="Tecnicatura Superior en Higiene y Seguridad en el Trabajo",
            resolucion_vigente="Res. 6183/25"
        )
        self.plan2 = PlanEstudio.objects.create(
            carrera=self.carrera2,
            materia=self.materia1,
            anio_carrera=1,
            carga_horaria_anual=96,
            carga_horaria_semanal=3
        )
        self.comision2 = Comision.objects.create(
            codigo_comision="COM_HIG_6183_2026",
            plan_estudio=self.plan2,
            anio_lectivo=2026
        )

        # Cursadas y Evaluaciones
        self.cursada1 = Cursada.objects.create(
            comision=self.comision1,
            alumno=self.alumno1,
            situacion_final="Promocionado"
        )
        self.eval1 = Evaluacion.objects.create(
            cursada=self.cursada1,
            instancia="Nota Final",
            nota=8.5,
            fecha=datetime.date(2026, 7, 10)
        )

        self.cursada2 = Cursada.objects.create(
            comision=self.comision1,
            alumno=self.alumno2,
            situacion_final="Regular"
        )

        self.cursada3 = Cursada.objects.create(
            comision=self.comision2,
            alumno=self.alumno3,
            situacion_final="Promocionado"
        )

    def test_requiere_autenticacion_para_acceder_al_buscador(self):
        """Un usuario anónimo debe ser redirigido a la pantalla de login."""
        self.client.logout()
        response = self.client.get(reverse('gestion:buscador'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login:login'), response.url)

    def test_edad_calculada_dinamicamente(self):
        """La edad no debe estar en la BD y debe calcularse dinámicamente según la fecha actual."""
        today = datetime.date.today()
        expected_age_1 = today.year - 2000 - ((today.month, today.day) < (1, 13))
        self.assertEqual(self.persona1.edad, expected_age_1)

        expected_age_2 = today.year - 1995 - ((today.month, today.day) < (9, 18))
        self.assertEqual(self.persona2.edad, expected_age_2)

        # Persona sin fecha de nacimiento
        p_sin_fecha = Persona.objects.create(
            dni="99999999",
            nombre="Sin",
            apellido="Fecha",
            identidad="N"
        )
        self.assertIsNone(p_sin_fecha.edad)

    def test_buscador_view_renders_correctly(self):
        response = self.client.get(reverse('gestion:buscador'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Abeldaño Aquino, Gonzalo Daniel")
        self.assertContains(response, "Alegre, Aldana Micaela")
        self.assertContains(response, "contenedorResultados")
        self.assertContains(response, "toggleResultados")

    def test_formatear_carreras_con_resolucion_y_anios(self):
        dict_carreras = {
            ('Técnico Superior en Energía', 'Res. 794/01'): {1, 2, 3},
            ('Tecnicatura Superior en Higiene', 'Res. 320/13'): {1},
            ('Tecnicatura en Logística', ''): {1, 2},
        }
        res = formatear_carreras_con_resolucion(dict_carreras)
        self.assertIn('Técnico Superior en Energía (Res. 794/01) (1°, 2° y 3° Año)', res)
        self.assertIn('Tecnicatura Superior en Higiene (Res. 320/13) (1° Año)', res)
        self.assertIn('Tecnicatura en Logística (1° y 2° Año)', res)

    def test_busqueda_por_dni_con_y_sin_formato(self):
        # DNI exacto
        response = self.client.post(reverse('gestion:buscador'), {'q': '45039996'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Abeldaño Aquino")

        # DNI con puntos
        response = self.client.post(reverse('gestion:buscador'), {'q': '45.039.996'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Abeldaño Aquino")

    def test_busqueda_por_cuil(self):
        response = self.client.post(reverse('gestion:buscador'), {'q': '20450399966'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Abeldaño Aquino")

    def test_busqueda_por_localidad(self):
        response = self.client.post(reverse('gestion:buscador'), {'localidad': 'Moreno'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Abeldaño Aquino")
        self.assertNotContains(response, "Alegre, Aldana Micaela")

    def test_filtro_por_carrera_sin_importar_plan(self):
        """Al filtrar por el nombre de la carrera, deben mostrarse todos los estudiantes sin importar la resolución/plan."""
        response = self.client.post(reverse('gestion:buscador'), {
            'carrera_nombre': 'Tecnicatura Superior en Higiene y Seguridad en el Trabajo'
        })
        self.assertEqual(response.status_code, 200)
        # Alumno 1 y 2 cursan Res. 320/13 y Alumno 3 cursa Res. 6183/25 -> Todos deben aparecer
        self.assertContains(response, "Abeldaño Aquino")
        self.assertContains(response, "Alegre, Aldana Micaela")
        self.assertContains(response, "Frette, Sam")

    def test_filtro_por_plan_estudio_especifico(self):
        """Al filtrar por un plan/resolución específico, solo se muestran los estudiantes de ese plan."""
        # Filtrar por Res. 6183/25
        response = self.client.post(reverse('gestion:buscador'), {'plan_id': 'HIGIENE-6183'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Frette, Sam")
        self.assertNotContains(response, "Abeldaño Aquino")
        self.assertNotContains(response, "Alegre, Aldana Micaela")

        # Filtrar por Res. 320/13
        response2 = self.client.post(reverse('gestion:buscador'), {'plan_id': 'HIGIENE-320'})
        self.assertEqual(response2.status_code, 200)
        self.assertContains(response2, "Abeldaño Aquino")
        self.assertContains(response2, "Alegre, Aldana Micaela")
        self.assertNotContains(response2, "Frette, Sam")

    def test_filtro_por_identidad_genero(self):
        """Debe filtrar correctamente por identidad de género (M, F, I, N)."""
        # Filtrar por Indistinto (I)
        response_i = self.client.post(reverse('gestion:buscador'), {'genero': 'I'})
        self.assertEqual(response_i.status_code, 200)
        self.assertContains(response_i, "Frette, Sam")
        self.assertNotContains(response_i, "Abeldaño Aquino")
        self.assertNotContains(response_i, "Alegre, Aldana Micaela")

        # Filtrar por Femenino (F)
        response_f = self.client.post(reverse('gestion:buscador'), {'genero': 'F'})
        self.assertEqual(response_f.status_code, 200)
        self.assertContains(response_f, "Alegre, Aldana Micaela")
        self.assertNotContains(response_f, "Abeldaño Aquino")
        self.assertNotContains(response_f, "Frette, Sam")

        # Filtrar por Masculino (M)
        response_m = self.client.post(reverse('gestion:buscador'), {'genero': 'M'})
        self.assertEqual(response_m.status_code, 200)
        self.assertContains(response_m, "Abeldaño Aquino")
        self.assertNotContains(response_m, "Alegre, Aldana Micaela")
        self.assertNotContains(response_m, "Frette, Sam")

    def test_filtro_por_nacionalidad(self):
        """Debe filtrar de forma exacta u optimizada por nacionalidad."""
        # Filtrar por Uruguaya
        response = self.client.post(reverse('gestion:buscador'), {'nacionalidad': 'Uruguaya'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Frette, Sam")
        self.assertNotContains(response, "Abeldaño Aquino")
        self.assertNotContains(response, "Alegre, Aldana Micaela")

        # Filtrar por Argentina
        response_arg = self.client.post(reverse('gestion:buscador'), {'nacionalidad': 'Argentina'})
        self.assertEqual(response_arg.status_code, 200)
        self.assertContains(response_arg, "Abeldaño Aquino")
        self.assertContains(response_arg, "Alegre, Aldana Micaela")
        self.assertNotContains(response_arg, "Frette, Sam")

    def test_filtro_por_anio_cursada(self):
        response = self.client.post(reverse('gestion:buscador'), {'anio': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Abeldaño Aquino")

    def test_paginacion_configurable(self):
        response = self.client.post(reverse('gestion:buscador'), {'page_size': '10', 'page': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_obj', response.context)
        self.assertEqual(response.context['page_size'], 10)

    def test_api_alumno_detalle_json_con_genero_y_sin_correo_ficticio(self):
        # Alumno con correo real
        response1 = self.client.get(reverse('gestion:alumno_detalle_json', kwargs={'dni': '45039996'}))
        self.assertEqual(response1.status_code, 200)
        json1 = response1.json()
        self.assertEqual(json1['personal']['mail'], 'gonzalodaniel2107@gmail.com')
        self.assertEqual(json1['personal']['genero_sigla'], 'M')
        self.assertEqual(json1['personal']['genero_desc'], 'Masculino')

        # Alumno sin correo especificado
        response2 = self.client.get(reverse('gestion:alumno_detalle_json', kwargs={'dni': '39110038'}))
        self.assertEqual(response2.status_code, 200)
        json2 = response2.json()
        self.assertEqual(json2['personal']['mail'], '')
        self.assertEqual(json2['personal']['genero_sigla'], 'F')
        self.assertEqual(json2['personal']['genero_desc'], 'Femenino')

        # Alumno con género Indistinto ('I')
        response3 = self.client.get(reverse('gestion:alumno_detalle_json', kwargs={'dni': '41000000'}))
        self.assertEqual(response3.status_code, 200)
        json3 = response3.json()
        self.assertEqual(json3['personal']['genero_sigla'], 'I')
        self.assertEqual(json3['personal']['genero_desc'], 'Indistinto')
        self.assertEqual(json3['personal']['nacionalidad'], 'Uruguaya')

    def test_descargar_libro_matriz_excel(self):
        response = self.client.get(reverse('gestion:descargar_libro_matriz_carrera', kwargs={'codigo_carrera': 'HIGIENE-320'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertTrue(len(response.content) > 0)

    def test_descargar_plantilla_alumnos_excel(self):
        response = self.client.get(reverse('gestion:descargar_plantilla_alumnos'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertIn('Plantilla_Carga_Alumnos', response['Content-Disposition'])

    def test_importar_alumnos_excel_valido(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Carga de Alumnos"
        ws.append(["DNI", "Apellido", "Nombre", "Carrera", "Año", "CUIL", "Fecha Nac", "Género", "Nacionalidad", "Localidad", "Domicilio", "Teléfono", "Mail"])
        ws.append(["48123456", "Rodríguez", "Lucas", "Tecnicatura Superior en Higiene", 1, "20481234568", "10/05/2003", "Masculino", "Argentina", "General Rodríguez", "Belgrano 450", "1144332211", "lucas.rodriguez@gmail.com"])
        ws.append(["49654321", "Fernández", "Camila", "", "", "", "", "Femenino", "", "Moreno", "", "", ""])
        ws.append(["50111222", "López", "Alex", "", "", "", "", "Indistinto", "Mexicana", "Luján", "", "", ""])
        
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        uploaded_file = SimpleUploadedFile("test_alumnos.xlsx", buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response = self.client.post(reverse('gestion:importar_alumnos'), {'archivo_excel': uploaded_file})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['creados'], 3)

        p1 = Persona.objects.get(dni="48123456")
        self.assertEqual(p1.apellido, "Rodríguez")
        self.assertEqual(p1.nombre, "Lucas")
        self.assertEqual(p1.mail, "lucas.rodriguez@gmail.com")
        self.assertEqual(p1.identidad, "M")

        p2 = Persona.objects.get(dni="49654321")
        self.assertEqual(p2.apellido, "Fernández")
        self.assertEqual(p2.nombre, "Camila")
        self.assertIsNone(p2.mail)
        self.assertEqual(p2.identidad, "F")

        p3 = Persona.objects.get(dni="50111222")
        self.assertEqual(p3.apellido, "López")
        self.assertEqual(p3.nombre, "Alex")
        self.assertEqual(p3.identidad, "I")
        self.assertEqual(p3.genero_descripcion, "Indistinto")
        self.assertEqual(p3.nacionalidad, "Mexicana")

    def test_imprimir_estado_academico(self):
        response = self.client.get(reverse('gestion:imprimir_estado_academico', kwargs={'dni': '45039996'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CONSTANCIA DE ESTADO ACADÉMICO")
        self.assertContains(response, "Abeldaño Aquino, Gonzalo Daniel")
        self.assertContains(response, "Identidad de Género")

    def test_ui_botones_docentes_y_cargar_alumnos(self):
        """Verifica que el botón de Buscar Docentes esté en primer lugar y Cargar Alumnos tenga su desplegable con ambas opciones."""
        response = self.client.get(reverse('gestion:buscador'))
        self.assertEqual(response.status_code, 200)
        # Botón Buscar Docentes
        self.assertContains(response, "Buscar Docentes")
        self.assertContains(response, reverse('gestion:docentes'))
        # Botón desplegable Cargar Alumnos
        self.assertContains(response, "Cargar Alumnos")
        self.assertContains(response, "dropdownCargarAlumnos")
        # Opción 1: Alta de Alumnos
        self.assertContains(response, "Alta de Alumnos")
        self.assertContains(response, reverse('carga_alumnos:index'))
        # Opción 2: Carga mediante Excel
        self.assertContains(response, "Carga mediante Excel (.xlsx)")
        self.assertContains(response, "abrirModalImportar()")

    def test_modulo_docentes_busqueda_y_render(self):
        """Verifica la vista del módulo de docentes y su buscador."""
        p_doc = Persona.objects.create(
            dni="20123456",
            cuil="20201234562",
            nombre="Esteban",
            apellido="Quito",
            localidad="General Rodríguez"
        )
        Docente.objects.create(persona=p_doc, titulo_mn="Ingeniero en Sistemas")

        response = self.client.get(reverse('gestion:docentes'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Buscador de Docentes")
        self.assertContains(response, "Quito, Esteban")
        self.assertContains(response, "Ingeniero en Sistemas")

        # Búsqueda por DNI
        res_busq = self.client.get(reverse('gestion:docentes'), {'q': '20123456'})
        self.assertEqual(res_busq.status_code, 200)
        self.assertContains(res_busq, "Quito, Esteban")

        # Búsqueda sin resultados
        res_vacio = self.client.get(reverse('gestion:docentes'), {'q': 'Inexistente9999'})
        self.assertEqual(res_vacio.status_code, 200)
        self.assertContains(res_vacio, "0 resultados")

    def test_modulo_docentes_importar_excel(self):
        """Verifica la importación de docentes desde un archivo Excel."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Docentes"
        ws.append(["DNI", "Apellido", "Nombre", "Título / Matrícula", "CUIL", "Teléfono", "Mail"])
        ws.append(["33444555", "Pérez", "Juan Carlos", "Licenciado en Seguridad e Higiene", "20334445558", "1133221100", "juan.perez@isft188.edu.ar"])

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        uploaded_file = SimpleUploadedFile("test_docentes.xlsx", buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response = self.client.post(reverse('gestion:importar_docentes'), {'archivo_excel': uploaded_file})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['creados'], 1)

        doc = Docente.objects.get(persona__dni="33444555")
        self.assertEqual(doc.persona.apellido, "Pérez")
        self.assertEqual(doc.persona.nombre, "Juan Carlos")
        self.assertEqual(doc.titulo_mn, "Licenciado en Seguridad e Higiene")

    def test_validacion_cuil_detallada(self):
        from gestion.validaciones import validar_cuil_detallado

        # 1. CUIL exitoso
        formateado, err = validar_cuil_detallado("27391100387", dni_val="39110038")
        self.assertIsNone(err)
        self.assertEqual(formateado, "27-39110038-7")

        # 2. Dígito verificador erróneo: debe explicar el dígito esperado
        _, err_digito = validar_cuil_detallado("27391100389", dni_val="39110038")
        self.assertIsNotNone(err_digito)
        self.assertIn("El número de CUIL no es correcto", err_digito)
        self.assertIn("dígito verificador 9", err_digito)
        self.assertIn("debe terminar en 7", err_digito)

        # 3. Disparidad entre DNI y números centrales
        _, err_dni = validar_cuil_detallado("20391100382", dni_val="45039996")
        self.assertIsNotNone(err_dni)
        self.assertIn("no coinciden con el DNI ingresado", err_dni)

        # 4. Longitud incorrecta
        _, err_len = validar_cuil_detallado("203911003", dni_val="3911003")
        self.assertIsNotNone(err_len)
        self.assertIn("debe tener exactamente 11 números", err_len)

        # 5. Prefijo incorrecto
        _, err_pref = validar_cuil_detallado("15391100384", dni_val="39110038")
        self.assertIsNotNone(err_pref)
        self.assertIn("el prefijo '15' no es válido", err_pref)

    def test_alta_docente_individual(self):
        response_get = self.client.get(reverse('gestion:alta_docente'))
        self.assertEqual(response_get.status_code, 200)
        self.assertTemplateUsed(response_get, 'gestion/docentes/alta.html')

        # Alta con CUIL y DNI válidos
        payload_ok = {
            'dni': '28456789',
            'cuil': '20-28456789-8',
            'nombre': 'Martín',
            'apellido': 'Gutiérrez',
            'fecha_nacimiento': '1982-06-15',
            'identidad': 'M',
            'nacionalidad': 'Argentina',
            'localidad': 'Luján',
            'domicilio': 'San Martín 450',
            'telefono': '+54 9 2323 123456',
            'mail': 'martin.gutierrez@isft188.edu.ar',
            'titulo_mn': 'Profesor en Química / MN 8765',
        }
        response_post = self.client.post(reverse('gestion:alta_docente'), data=payload_ok)
        self.assertEqual(response_post.status_code, 302)
        self.assertRedirects(response_post, reverse('gestion:paso2_confirmacion_docentes'))

        # Confirmar en la matriz de docentes
        res_conf = self.client.post(
            reverse('gestion:paso2_confirmacion_docentes'),
            data={'accion': 'confirmar'},
            follow=True
        )
        self.assertEqual(res_conf.status_code, 200)

        docente_creado = Docente.objects.filter(persona__dni='28456789').first()
        self.assertIsNotNone(docente_creado)
        self.assertEqual(docente_creado.persona.apellido, 'Gutiérrez')
        self.assertEqual(docente_creado.titulo_mn, 'Profesor en Química / MN 8765')

    def test_persona_datos_json_y_edicion_alumno(self):
        # 1. Obtener JSON de datos del alumno
        res_json = self.client.get(reverse('gestion:persona_datos_json', kwargs={'tipo': 'alumno', 'identificador': self.persona1.dni}))
        self.assertEqual(res_json.status_code, 200)
        data = res_json.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['dni'], self.persona1.dni)
        self.assertEqual(data['nombre'], self.persona1.nombre)

        # 2. Editar datos del alumno
        edit_payload = {
            'dni': self.persona1.dni,
            'cuil': self.persona1.cuil,
            'nombre': 'Gonzalo Modificado',
            'apellido': 'Abeldaño Modificado',
            'fecha_nacimiento': '2000-01-13',
            'identidad': 'M',
            'nacionalidad': 'Argentina',
            'localidad': 'General Rodríguez',
            'domicilio': 'Avenida Siempre Viva 742',
            'telefono': '+5491122334455',
            'mail': 'nuevo.correo@gmail.com',
            'legajo': 'LEG-EDITADO-999',
        }
        res_edit = self.client.post(reverse('gestion:persona_editar', kwargs={'tipo': 'alumno', 'identificador': self.persona1.dni}), data=edit_payload)
        self.assertEqual(res_edit.status_code, 200)
        self.assertTrue(res_edit.json()['success'])

        self.persona1.refresh_from_db()
        self.assertEqual(self.persona1.nombre, 'Gonzalo Modificado')
        self.assertEqual(self.persona1.localidad, 'General Rodríguez')
        self.assertEqual(self.alumno1.persona.alumno_profile.legajo, 'LEG-EDITADO-999')

    def test_editar_y_eliminar_docente(self):
        # Crear docente para prueba
        p_doc = Persona.objects.create(
            dni="22334455",
            cuil="27223344556",
            nombre="Clara",
            apellido="Zárate",
            fecha_nacimiento=datetime.date(1980, 5, 20),
            identidad="F",
            nacionalidad="Argentina",
            localidad="Pilar"
        )
        doc = Docente.objects.create(persona=p_doc, titulo_mn="Licenciada en Bioquímica")

        # Editar docente
        edit_payload = {
            'dni': '22334455',
            'cuil': '27-22334455-6',
            'nombre': 'Clara Eugenia',
            'apellido': 'Zárate de Gómez',
            'fecha_nacimiento': '1980-05-20',
            'identidad': 'F',
            'nacionalidad': 'Argentina',
            'localidad': 'Pilar',
            'titulo_mn': 'Doctora en Bioquímica',
        }
        res_edit = self.client.post(reverse('gestion:persona_editar', kwargs={'tipo': 'docente', 'identificador': '22334455'}), data=edit_payload)
        self.assertEqual(res_edit.status_code, 200)
        self.assertTrue(res_edit.json()['success'])

        doc.refresh_from_db()
        self.assertEqual(doc.titulo_mn, 'Doctora en Bioquímica')
        self.assertEqual(doc.persona.nombre, 'Clara Eugenia')

        # Eliminar docente
        res_del = self.client.post(reverse('gestion:persona_eliminar', kwargs={'tipo': 'docente', 'identificador': '22334455'}))
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.json()['success'])
        self.assertFalse(Docente.objects.filter(persona__dni='22334455').exists())

    def test_docentes_filtros_y_paginacion(self):
        # Crear varios docentes con diferentes atributos
        p1 = Persona.objects.create(dni="31111111", cuil="20311111117", nombre="Ana", apellido="Álvarez", identidad="F", nacionalidad="Argentina", localidad="Moreno", fecha_nacimiento=datetime.date(1985, 1, 1))
        Docente.objects.create(persona=p1, titulo_mn="Ingeniera")

        p2 = Persona.objects.create(dni="32222222", cuil="20322222223", nombre="Bruno", apellido="Benítez", identidad="M", nacionalidad="Paraguaya", localidad="Luján", fecha_nacimiento=datetime.date(1990, 2, 2))
        Docente.objects.create(persona=p2, titulo_mn="Arquitecto")

        # Filtro por género F
        res_f = self.client.get(reverse('gestion:docentes'), {'genero': 'F'})
        self.assertEqual(res_f.status_code, 200)
        self.assertContains(res_f, "Álvarez, Ana")
        self.assertNotContains(res_f, "Benítez, Bruno")

        # Filtro por nacionalidad Paraguaya
        res_nac = self.client.get(reverse('gestion:docentes'), {'nacionalidad': 'Paraguaya'})
        self.assertEqual(res_nac.status_code, 200)
        self.assertContains(res_nac, "Benítez, Bruno")
        self.assertNotContains(res_nac, "Álvarez, Ana")

        # Filtro por localidad Moreno
        res_loc = self.client.get(reverse('gestion:docentes'), {'localidad': 'Moreno'})
        self.assertEqual(res_loc.status_code, 200)
        self.assertContains(res_loc, "Álvarez, Ana")
        self.assertNotContains(res_loc, "Benítez, Bruno")

        # Selector de registros por página
        res_page = self.client.get(reverse('gestion:docentes'), {'page_size': '10'})
        self.assertEqual(res_page.status_code, 200)
        self.assertEqual(res_page.context['page_size'], 10)

    def test_docentes_ui_formato_dni_y_colapsable(self):
        p = Persona.objects.create(
            dni="38123456",
            cuil="20381234567",
            nombre="Martín",
            apellido="Gómez",
            identidad="M",
            nacionalidad="Argentina",
            localidad="General Rodríguez"
        )
        Docente.objects.create(persona=p, titulo_mn="Profesor Universitario")

        res = self.client.get(reverse('gestion:docentes'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "38.123.456")
        self.assertContains(res, "toggleResultadosDocentes")
        self.assertContains(res, "contenedorResultadosDocentes")
        self.assertContains(res, "modalExpedienteDocente")
        self.assertContains(res, "bg-indigo-600 hover:bg-indigo-500")

    def test_docente_expediente_api_json(self):
        p = Persona.objects.create(
            dni="35999888",
            cuil="20359998884",
            nombre="Valeria",
            apellido="Solís",
            identidad="F",
            nacionalidad="Uruguaya",
            localidad="Luján",
            mail="valeria.solis@isft188.edu.ar",
            fecha_nacimiento=datetime.date(1988, 3, 15)
        )
        doc = Docente.objects.create(persona=p, titulo_mn="Licenciada en Sistemas")

        res = self.client.get(reverse('gestion:docente_detalle_json', kwargs={'dni': '35999888'}))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['personal']['dni'], '35.999.888')
        self.assertEqual(data['personal']['cuil'], '20-35999888-4')
        self.assertEqual(data['personal']['nombre_completo'], 'Prof. Solís, Valeria')
        self.assertEqual(data['personal']['titulo_mn'], 'Licenciada en Sistemas')
        self.assertEqual(data['personal']['genero_desc'], 'Femenino')
        self.assertEqual(data['personal']['nacionalidad'], 'Uruguaya')
        self.assertIn('resumen_docente', data)
        self.assertIn('comisiones', data)

    def test_alta_docente_y_matriz_confirmacion(self):
        payload = {
            'dni': '39888777',
            'cuil': '20-39888777-9',
            'nombre': 'Esteban',
            'apellido': 'Quito',
            'fecha_nacimiento': '1992-04-10',
            'identidad': 'M',
            'nacionalidad': 'Otra',
            'nacionalidad_otra': 'Canadiense',
            'localidad': 'Mercedes',
            'domicilio': 'Calle Falsa 123',
            'telefono': '11-5555-4444',
            'mail': 'esteban.quito@gmail.com',
            'titulo_mn': 'Magíster en Educación',
        }

        res_alta = self.client.post(reverse('gestion:alta_docente'), data=payload)
        self.assertEqual(res_alta.status_code, 302)
        self.assertRedirects(res_alta, reverse('gestion:paso2_confirmacion_docentes'))

        session_list = self.client.session.get('carga_docentes_temp_data_list', [])
        self.assertEqual(len(session_list), 1)
        self.assertEqual(session_list[0]['dni'], '39888777')
        self.assertEqual(session_list[0]['nacionalidad'], 'Canadiense')

        res_matriz = self.client.get(reverse('gestion:paso2_confirmacion_docentes'))
        self.assertEqual(res_matriz.status_code, 200)
        self.assertContains(res_matriz, "39.888.777")
        self.assertContains(res_matriz, "Quito, Esteban")
        self.assertContains(res_matriz, "Canadiense")

        res_confirmar = self.client.post(
            reverse('gestion:paso2_confirmacion_docentes'),
            data={'accion': 'confirmar'}
        )
        self.assertEqual(res_confirmar.status_code, 302)
        self.assertRedirects(res_confirmar, reverse('gestion:docentes'))

        p = Persona.objects.get(dni='39888777')
        self.assertEqual(p.apellido, 'Quito')
        self.assertEqual(p.nombre, 'Esteban')
        self.assertEqual(p.nacionalidad, 'Canadiense')
        self.assertEqual(p.localidad, 'Mercedes')

        doc = Docente.objects.get(persona=p)
        self.assertEqual(doc.titulo_mn, 'Magíster en Educación')


