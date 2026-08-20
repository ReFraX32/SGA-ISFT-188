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

        # Carrera y Materias
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

    def test_filtro_por_carrera(self):
        response = self.client.post(reverse('gestion:buscador'), {'carrera': 'HIGIENE-320'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Abeldaño Aquino")
        self.assertContains(response, "Alegre, Aldana Micaela")

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
        
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        uploaded_file = SimpleUploadedFile("test_alumnos.xlsx", buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response = self.client.post(reverse('gestion:importar_alumnos'), {'archivo_excel': uploaded_file})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['creados'], 2)

        p1 = Persona.objects.get(dni="48123456")
        self.assertEqual(p1.apellido, "Rodríguez")
        self.assertEqual(p1.nombre, "Lucas")
        self.assertEqual(p1.mail, "lucas.rodriguez@gmail.com")

        p2 = Persona.objects.get(dni="49654321")
        self.assertEqual(p2.apellido, "Fernández")
        self.assertEqual(p2.nombre, "Camila")
        self.assertIsNone(p2.mail)

    def test_imprimir_estado_academico(self):
        response = self.client.get(reverse('gestion:imprimir_estado_academico', kwargs={'dni': '45039996'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CONSTANCIA DE ESTADO ACADÉMICO")
        self.assertContains(response, "Abeldaño Aquino, Gonzalo Daniel")
        self.assertContains(response, "Identidad de Género")
