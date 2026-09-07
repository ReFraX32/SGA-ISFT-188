from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from gestion.models import Carrera, Materia, PlanEstudio
from carreras.forms import CarreraForm, CarreraEditForm


class CarrerasModuleTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testadmin', password='password123')
        self.client.login(username='testadmin', password='password123')

        # Carrera de prueba con plan de estudio en 2 años
        self.carrera = Carrera.objects.create(
            codigo_carrera='TEST-SOFT-188',
            nombre_carrera='Tecnicatura Superior en Desarrollo de Software Test',
            resolucion_vigente='Res. 6183/19',
            resolucion_anterior='Res. 320/09'
        )

        self.mat1 = Materia.objects.create(
            codigo_materia='SOFT-101',
            nombre_materia='Algoritmos y Estructuras de Datos'
        )
        self.mat2 = Materia.objects.create(
            codigo_materia='SOFT-201',
            nombre_materia='Bases de Datos Avanzadas'
        )

        self.plan1 = PlanEstudio.objects.create(
            carrera=self.carrera,
            materia=self.mat1,
            anio_carrera=1,
            modalidad='Anual',
            carga_horaria_semanal=Decimal('4.0'),
            carga_horaria_anual=128,
            correlatividades=''
        )
        self.plan2 = PlanEstudio.objects.create(
            carrera=self.carrera,
            materia=self.mat2,
            anio_carrera=2,
            modalidad='1° Cuatrimestre',
            carga_horaria_semanal=Decimal('3.0'),
            carga_horaria_anual=64,
            correlatividades='SOFT-101'
        )

    def test_carrera_form_valid(self):
        form_data = {
            'codigo_carrera': 'NUEVA-CARRERA-188',
            'nombre_carrera': 'Tecnicatura en Inteligencia Artificial',
            'resolucion_vigente': 'Res. 100/26',
            'resolucion_anterior': '',
            'duracion_anios': 3,
        }
        form = CarreraForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_carrera_form_duplicate_code(self):
        form_data = {
            'codigo_carrera': 'TEST-SOFT-188',  # ya existe en setUp
            'nombre_carrera': 'Otra Carrera Duplicada',
            'resolucion_vigente': 'Res. 100/26',
            'duracion_anios': 3,
        }
        form = CarreraForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('codigo_carrera', form.errors)

    def test_carrera_form_invalid_code_format(self):
        form_data = {
            'codigo_carrera': 'CÓDIGO INVÁLIDO CON ESPACIOS!',
            'nombre_carrera': 'Carrera Test',
            'duracion_anios': 3,
        }
        form = CarreraForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('codigo_carrera', form.errors)

    def test_carreras_list_view_authenticated(self):
        response = self.client.get(reverse('carreras:carreras_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TEST-SOFT-188')
        self.assertContains(response, 'Tecnicatura Superior en Desarrollo de Software Test')

    def test_carreras_list_view_filter_search(self):
        response = self.client.get(reverse('carreras:carreras_list'), {'q': 'Desarrollo'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TEST-SOFT-188')

        response_empty = self.client.get(reverse('carreras:carreras_list'), {'q': 'InexistenteXYZ'})
        self.assertEqual(response_empty.status_code, 200)
        self.assertNotContains(response_empty, 'TEST-SOFT-188')

    def test_carrera_detalle_json(self):
        url = reverse('carreras:carrera_detalle_json', kwargs={'codigo_carrera': 'TEST-SOFT-188'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['codigo_carrera'], 'TEST-SOFT-188')
        self.assertEqual(data['total_materias'], 2)
        self.assertEqual(data['total_horas_anuales'], 192)
        # Verificar agrupamiento por año
        self.assertEqual(len(data['anios']), 2)
        self.assertEqual(data['anios'][0]['numero'], 1)
        self.assertEqual(data['anios'][0]['materias'][0]['codigo_materia'], 'SOFT-101')
        self.assertEqual(data['anios'][1]['numero'], 2)
        self.assertEqual(data['anios'][1]['materias'][0]['codigo_materia'], 'SOFT-201')

    def test_alta_carrera_flujo_dos_pasos(self):
        # Paso 1: Datos de la Carrera
        url_paso1 = reverse('carreras:alta_carrera')
        post_paso1 = {
            'codigo_carrera': 'ALTA-TEST-2026',
            'nombre_carrera': 'Tecnicatura en Ciberseguridad',
            'resolucion_vigente': 'Res. 999/26',
            'resolucion_anterior': '',
            'duracion_anios': 2,
        }
        resp1 = self.client.post(url_paso1, post_paso1)
        self.assertEqual(resp1.status_code, 302)
        self.assertRedirects(resp1, reverse('carreras:alta_carrera_matriz'))

        # Comprobar sesión
        session = self.client.session
        self.assertIn('carrera_borrador_datos', session)
        self.assertEqual(session['carrera_borrador_datos']['codigo_carrera'], 'ALTA-TEST-2026')

        # Paso 2: Matriz de Materias por Año
        url_paso2 = reverse('carreras:alta_carrera_matriz')
        post_paso2 = {
            'accion': 'guardar',
            'materia_codigo[]': ['CIBER-101', 'CIBER-201'],
            'materia_nombre[]': ['Seguridad en Redes', 'Criptografía Aplicada'],
            'materia_anio[]': ['1', '2'],
            'materia_modalidad[]': ['Anual', 'Anual'],
            'materia_hs_semanal[]': ['4', '4'],
            'materia_hs_anual[]': ['128', '128'],
            'materia_correlatividades[]': ['', 'CIBER-101'],
        }
        resp2 = self.client.post(url_paso2, post_paso2)
        self.assertEqual(resp2.status_code, 302)
        self.assertRedirects(resp2, reverse('carreras:carreras_list'))

        # Comprobar que se guardó en la base de datos
        carrera_creada = Carrera.objects.filter(codigo_carrera='ALTA-TEST-2026').first()
        self.assertIsNotNone(carrera_creada)
        self.assertEqual(carrera_creada.nombre_carrera, 'Tecnicatura en Ciberseguridad')
        self.assertEqual(carrera_creada.planes_estudio.count(), 2)

        # Materias creadas
        mat_redes = Materia.objects.filter(codigo_materia='CIBER-101').first()
        self.assertIsNotNone(mat_redes)
        self.assertEqual(mat_redes.nombre_materia, 'Seguridad en Redes')

    def test_carrera_editar_view(self):
        url = reverse('carreras:carrera_editar', kwargs={'codigo_carrera': 'TEST-SOFT-188'})
        post_data = {
            'nombre_carrera': 'Tecnicatura Superior en Software Modificada',
            'resolucion_vigente': 'Res. 9999/26',
            'resolucion_anterior': 'Res. 320/09',
        }
        resp = self.client.post(url, post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])

        self.carrera.refresh_from_db()
        self.assertEqual(self.carrera.nombre_carrera, 'Tecnicatura Superior en Software Modificada')
        self.assertEqual(self.carrera.resolucion_vigente, 'Res. 9999/26')

    def test_carrera_eliminar_view(self):
        carrera_temp = Carrera.objects.create(
            codigo_carrera='TEMP-ELIMINAR',
            nombre_carrera='Carrera Temporal'
        )
        url = reverse('carreras:carrera_eliminar', kwargs={'codigo_carrera': 'TEMP-ELIMINAR'})
        resp = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertFalse(Carrera.objects.filter(codigo_carrera='TEMP-ELIMINAR').exists())

    def test_imprimir_plan_estudio_view(self):
        url = reverse('carreras:imprimir_plan_estudio', kwargs={'codigo_carrera': 'TEST-SOFT-188'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TEST-SOFT-188')
        self.assertContains(response, 'Algoritmos y Estructuras de Datos')
        self.assertContains(response, 'Bases de Datos Avanzadas')
