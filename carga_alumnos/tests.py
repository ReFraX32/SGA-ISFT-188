from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.apps import apps
from .models import Alumno
from .views import SESSION_KEY


class CargaAlumnosTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username='admin_test',
            password='testpassword123',
            email='admin@isft188.edu.ar'
        )
        self.client.login(username='admin_test', password='testpassword123')

        self.alumno_payload = {
            'dni': '42345678',
            'cuil': '20-42345678-8',
            'nombre': 'Juan Carlos',
            'apellido': 'Pérez',
            'fecha_nacimiento': '2000-05-15',
            'genero': 'M',
            'email': 'juan.perez@isft188.edu.ar',
            'telefono': '+54 9 11 4455-6677',
            'direccion': 'Av. Mitre 1234',
            'localidad': 'General Rodríguez',
            'nacionalidad': 'Argentina',
        }

        # CUIL válido ANSES: 27-35111222-6 (suma pond. 93, mod 11 = 5 -> 11 - 5 = 6)
        self.alumno_payload_2 = {
            'dni': '35111222',
            'cuil': '27-35111222-6',
            'nombre': 'María Laura',
            'apellido': 'Gómez',
            'fecha_nacimiento': '1995-10-20',
            'genero': 'F',
            'email': 'maria.gomez@isft188.edu.ar',
            'telefono': '+54 9 11 8899-0011',
            'direccion': 'Calle San Martín 456',
            'localidad': 'Luján',
            'nacionalidad': 'Argentina',
        }

    def test_index_view_loads_paso1_directly(self):
        # El acceso al módulo debe cargar directamente el formulario de carga
        response = self.client.get(reverse('carga_alumnos:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'carga_alumnos/paso1_carga.html')
        self.assertContains(response, 'Ingreso de Datos del Alumno')

    def test_paso1_carga_get(self):
        response = self.client.get(reverse('carga_alumnos:paso1_carga'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ingreso de Datos del Alumno')
        self.assertContains(response, 'CUIL')
        self.assertContains(response, 'Localidad')
        self.assertNotContains(response, 'Código Postal')
        self.assertNotContains(response, 'País de Residencia')
        # Verificar que no aparecen textos de estándares técnicos en la UI
        self.assertNotContains(response, 'Estándares Activos')
        self.assertNotContains(response, 'RFC 5322')
        self.assertNotContains(response, 'ISO 8601')
        self.assertTemplateUsed(response, 'carga_alumnos/paso1_carga.html')

    def test_paso1_carga_post_valid_redirects_and_does_not_save_to_db(self):
        initial_count = Alumno.objects.count()
        response = self.client.post(reverse('carga_alumnos:paso1_carga'), data=self.alumno_payload)
        
        # Redirección a paso 2
        self.assertRedirects(response, reverse('carga_alumnos:paso2_confirmacion'))
        
        # La base de datos no debe haber cambiado en el paso 1
        self.assertEqual(Alumno.objects.count(), initial_count)
        
        # Debe haber guardado los datos en la matriz en sesión
        session = self.client.session
        self.assertIn(SESSION_KEY, session)
        self.assertIsInstance(session[SESSION_KEY], list)
        self.assertEqual(len(session[SESSION_KEY]), 1)
        self.assertEqual(session[SESSION_KEY][0]['dni'], '42345678')
        self.assertEqual(session[SESSION_KEY][0]['cuil'], '20-42345678-8')
        self.assertEqual(session[SESSION_KEY][0]['localidad'], 'General Rodríguez')

    def test_paso2_confirmacion_get_with_session(self):
        # Primero ejecutar paso 1
        self.client.post(reverse('carga_alumnos:paso1_carga'), data=self.alumno_payload)
        
        # Cargar matriz de confirmación
        response = self.client.get(reverse('carga_alumnos:paso2_confirmacion'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Matriz de Alumnos a Confirmar')
        self.assertContains(response, 'Confirmar y Guardar Alumno')
        self.assertContains(response, 'Modificar Datos')
        self.assertContains(response, 'Cargar Otro Alumno')
        self.assertContains(response, '42345678')
        self.assertContains(response, '20-42345678-8')
        self.assertContains(response, 'General Rodríguez')
        self.assertContains(response, 'Juan Carlos')
        self.assertContains(response, 'Pérez')
        self.assertNotContains(response, 'Microsoft Excel Online')
        self.assertNotContains(response, '=INSERTAR_ESTUDIANTE')

    def test_paso2_nuevo_alumno_retains_matrix_and_redirects_paso1(self):
        # Cargar alumno 1
        self.client.post(reverse('carga_alumnos:paso1_carga'), data=self.alumno_payload)
        self.assertIn(SESSION_KEY, self.client.session)

        # Pulsar 'Cargar Otro Alumno'
        response = self.client.post(reverse('carga_alumnos:paso2_confirmacion'), {'accion': 'nuevo_alumno'})
        self.assertRedirects(response, reverse('carga_alumnos:paso1_carga'))

        # La sesión debe conservar el alumno previo para la matriz
        self.assertIn(SESSION_KEY, self.client.session)
        self.assertEqual(len(self.client.session[SESSION_KEY]), 1)
        self.assertEqual(Alumno.objects.count(), 0)

    def test_paso2_cancelar_clears_session_and_redirects_paso1(self):
        # Guardar en sesión
        self.client.post(reverse('carga_alumnos:paso1_carga'), data=self.alumno_payload)
        self.assertIn(SESSION_KEY, self.client.session)

        # Cancelar
        response = self.client.post(reverse('carga_alumnos:paso2_confirmacion'), {'accion': 'cancelar'})
        self.assertRedirects(response, reverse('carga_alumnos:paso1_carga'))

        # La sesión debe estar limpia y la BD intacta
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertEqual(Alumno.objects.count(), 0)

    def test_paso2_modificar_extracts_student_and_redirects_paso1(self):
        # Guardar en sesión
        self.client.post(reverse('carga_alumnos:paso1_carga'), data=self.alumno_payload)
        self.assertIn(SESSION_KEY, self.client.session)

        # Modificar redirige a paso 1
        response = self.client.post(reverse('carga_alumnos:paso2_confirmacion'), {'accion': 'modificar'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'carga_alumnos/paso1_carga.html')
        # El formulario en paso 1 debe estar pre-poblado con los datos del alumno extraído
        self.assertEqual(response.context['form']['dni'].value(), '42345678')
        self.assertEqual(response.context['form']['cuil'].value(), '20-42345678-8')

    def test_carga_multiples_alumnos_en_matriz_y_confirmacion(self):
        # Cargar alumno 1
        r1 = self.client.post(reverse('carga_alumnos:paso1_carga'), data=self.alumno_payload)
        self.assertEqual(r1.status_code, 302)
        
        # Cargar alumno 2
        r2 = self.client.post(reverse('carga_alumnos:paso1_carga'), data=self.alumno_payload_2)
        self.assertEqual(r2.status_code, 302)

        # Ver la matriz: debe contener ambos alumnos en la misma vista sin deslizar
        response = self.client.get(reverse('carga_alumnos:paso2_confirmacion'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2 Alumnos en Tanda')
        self.assertContains(response, '42345678')
        self.assertContains(response, 'Juan Carlos')
        self.assertContains(response, '35111222')
        self.assertContains(response, 'María Laura')
        self.assertContains(response, 'Luján')

        # Confirmar ambos alumnos en un solo clic
        response = self.client.post(reverse('carga_alumnos:paso2_confirmacion'), {'accion': 'confirmar'})
        self.assertRedirects(response, reverse('carga_alumnos:paso1_carga'))

        # Sesión limpia
        self.assertNotIn(SESSION_KEY, self.client.session)

        # Ambos alumnos guardados en la BD
        self.assertEqual(Alumno.objects.count(), 2)
        self.assertTrue(Alumno.objects.filter(dni='42345678').exists())
        self.assertTrue(Alumno.objects.filter(dni='35111222').exists())

        # Sincronizados con el modelo central gestion
        if apps.is_installed('gestion'):
            PersonaModel = apps.get_model('gestion', 'Persona')
            self.assertTrue(PersonaModel.objects.filter(dni='42345678').exists())
            self.assertTrue(PersonaModel.objects.filter(dni='35111222').exists())

    def test_eliminar_fila_de_la_matriz(self):
        # Cargar alumno 1 y alumno 2
        self.client.post(reverse('carga_alumnos:paso1_carga'), data=self.alumno_payload)
        self.client.post(reverse('carga_alumnos:paso1_carga'), data=self.alumno_payload_2)

        # Quitar la fila 0 (Juan Carlos Pérez)
        response = self.client.post(reverse('carga_alumnos:paso2_confirmacion'), {
            'accion': 'eliminar_fila',
            'fila_index': '0',
        })
        self.assertRedirects(response, reverse('carga_alumnos:paso2_confirmacion'))

        # La matriz ahora solo debe tener 1 alumno (María Laura)
        session = self.client.session
        self.assertEqual(len(session[SESSION_KEY]), 1)
        self.assertEqual(session[SESSION_KEY][0]['dni'], '35111222')

    def test_paso1_carga_post_invalid_displays_compact_error_cartel_and_red_indicators(self):
        # Enviar carga con datos inválidos: CUIL con dígito incorrecto y menor de 15 años
        payload_invalido = self.alumno_payload.copy()
        payload_invalido['cuil'] = '20-42345678-0'  # Inválido: debe ser 8
        payload_invalido['fecha_nacimiento'] = '2020-05-15'  # Menor de 15 años

        response = self.client.post(reverse('carga_alumnos:paso1_carga'), data=payload_invalido)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'carga_alumnos/paso1_carga.html')

        # Verificar presencia del cartel de errores compacto en rojo
        self.assertContains(response, 'id="cartelErroresFormulario"')
        self.assertContains(response, 'Por favor, revisá los campos señalados en rojo')
        self.assertContains(response, 'alert-error-card')

        # Verificar mensajes claros y no técnicos
        self.assertContains(response, 'El número de CUIL no es correcto')
        self.assertContains(response, 'La edad mínima para ingresar es de 15 años')

        # Verificar presencia de indicadores y clases rojas
        self.assertContains(response, '!border-rose-500')
        self.assertContains(response, 'text-rose-400')

    def test_carga_alumno_extranjero_con_dni_extranjero_y_cuil_oficial(self):
        # Cargar alumno extranjero con DNI de extranjero (RENAPER), CUIL oficial (ANSES), teléfono internacional y nacionalidad 'Otra'
        payload_extranjero = {
            'dni': '94123456',
            'cuil': '20-94123456-9',
            'nombre': 'Jean Pierre',
            'apellido': 'Dubois',
            'fecha_nacimiento': '1998-03-22',
            'genero': 'M',
            'email': 'jean.dubois@correo.com',
            'telefono': '+33 6 12 34 56 78',
            'direccion': 'Rue de la Paix 10',
            'localidad': 'Otra Localidad',
            'nacionalidad': 'Otra',
            'nacionalidad_otra': 'Francesa',
        }

        response = self.client.post(reverse('carga_alumnos:paso1_carga'), data=payload_extranjero)
        self.assertRedirects(response, reverse('carga_alumnos:paso2_confirmacion'))

        # Debe haberse guardado en sesión con DNI, CUIL normalizado y nacionalidad 'Francesa'
        session = self.client.session
        self.assertIn(SESSION_KEY, session)
        alumno_sesion = session[SESSION_KEY][0]
        self.assertEqual(alumno_sesion['dni'], '94123456')
        self.assertEqual(alumno_sesion['cuil'], '20-94123456-9')
        self.assertEqual(alumno_sesion['telefono'], '+33 6 12 34 56 78')
        self.assertEqual(alumno_sesion['nacionalidad'], 'Francesa')

        # Confirmar en la base de datos
        res_confirmar = self.client.post(reverse('carga_alumnos:paso2_confirmacion'), {'accion': 'confirmar'})
        self.assertRedirects(res_confirmar, reverse('carga_alumnos:paso1_carga'))

        guardado = Alumno.objects.get(dni='94123456')
        self.assertEqual(guardado.nacionalidad, 'Francesa')
        self.assertEqual(guardado.cuil, '20-94123456-9')

    def test_rechazo_pasaporte_y_cdi_en_formulario(self):
        # Verificar que el sistema rechaza pasaportes alfanuméricos y formatos no oficiales de CUIL
        payload_invalido = {
            'dni': 'PAS-F9876543',
            'cuil': 'CDI-9876543',
            'nombre': 'Jean Pierre',
            'apellido': 'Dubois',
            'fecha_nacimiento': '1998-03-22',
            'genero': 'M',
            'email': 'jean.dubois@correo.com',
            'telefono': '+33 6 12 34 56 78',
            'direccion': 'Rue de la Paix 10',
            'localidad': 'Otra Localidad',
            'nacionalidad': 'Otra',
            'nacionalidad_otra': 'Francesa',
        }

        response = self.client.post(reverse('carga_alumnos:paso1_carga'), data=payload_invalido)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El DNI debe contener solo números.')
        self.assertContains(response, 'El CUIL debe contener solo números y guiones.')
