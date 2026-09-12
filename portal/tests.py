from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate

from gestion.models import (
    Persona, Alumno, Docente, Carrera, Materia, PlanEstudio,
    Comision, ComisionDocente, Cursada, Evaluacion
)

User = get_user_model()


class PortalAndAuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Admin Directivo
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='mde123',
            is_staff=True,
            is_superuser=True,
        )

        # 2. Carrera y materias
        self.carrera = Carrera.objects.create(
            codigo_carrera='DS-188',
            nombre_carrera='Tecnicatura en Desarrollo de Software',
            resolucion_vigente='Res. 6183/19',
        )
        self.mat1 = Materia.objects.create(
            codigo_materia='PROG1',
            nombre_materia='Programación I'
        )
        self.plan1 = PlanEstudio.objects.create(
            carrera=self.carrera,
            materia=self.mat1,
            anio_carrera=1,
            modalidad='Anual',
            carga_horaria_semanal=Decimal('4.0'),
            carga_horaria_anual=128
        )
        self.comision = Comision.objects.create(
            codigo_comision='COM-DS-1A',
            plan_estudio=self.plan1,
            anio_lectivo=2026,
            turno='Vespertino',
            division='A'
        )

        # 3. Docente
        self.persona_doc = Persona.objects.create(
            dni='25111222',
            nombre='Carlos',
            apellido='López',
            mail='carlos.lopez@isft188.edu.ar',
            telefono='2364112233'
        )
        self.docente = Docente.objects.create(
            persona=self.persona_doc,
            titulo_mn='Lic. en Sistemas'
        )
        ComisionDocente.objects.create(
            comision=self.comision,
            docente=self.docente,
            rol='Titular'
        )

        # 4. Alumno
        self.persona_alu = Persona.objects.create(
            dni='44333222',
            nombre='Valentina',
            apellido='Rossi',
            mail='valentina.rossi@alumnos.isft188.edu.ar',
            telefono='2364556677'
        )
        self.alumno = Alumno.objects.create(
            persona=self.persona_alu,
            legajo='LEG-2025-001'
        )
        self.cursada = Cursada.objects.create(
            alumno=self.alumno,
            comision=self.comision,
            porcentaje_asistencia=Decimal('88.5'),
            situacion_final='Regular'
        )
        Evaluacion.objects.create(
            cursada=self.cursada,
            instancia='1° Parcial',
            nota=Decimal('8.50')
        )
        Evaluacion.objects.create(
            cursada=self.cursada,
            instancia='Examen Final',
            nota=Decimal('9.00')
        )

    def test_dni_auth_backend_for_alumno(self):
        # Autenticación con DNI y clave por defecto 123456789
        user = authenticate(username='44.333.222', password='123456789')
        self.assertIsNotNone(user)
        self.assertEqual(user.username, '44333222')
        self.assertFalse(user.is_staff)

    def test_dni_auth_backend_for_docente(self):
        # Autenticación con DNI de docente y clave 123456789
        user = authenticate(username='25111222', password='123456789')
        self.assertIsNotNone(user)
        self.assertEqual(user.username, '25111222')
        self.assertFalse(user.is_staff)

    def test_dni_auth_backend_bad_password(self):
        user = authenticate(username='44333222', password='wrongpassword')
        self.assertIsNone(user)

    def test_login_redirect_for_alumno(self):
        response = self.client.post(reverse('login:login'), {
            'username': '44333222',
            'password': '123456789',
        })
        self.assertRedirects(response, reverse('portal:alumno'))

    def test_login_redirect_for_docente(self):
        response = self.client.post(reverse('login:login'), {
            'username': '25111222',
            'password': '123456789',
        })
        self.assertRedirects(response, reverse('portal:docente'))

    def test_login_redirect_for_admin(self):
        response = self.client.post(reverse('login:login'), {
            'username': 'admin',
            'password': 'mde123',
        })
        self.assertRedirects(response, reverse('gestion:buscador'))

    def test_portal_alumno_view_authenticated(self):
        self.client.login(username='44333222', password='123456789')
        response = self.client.get(reverse('portal:alumno'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rossi, Valentina')
        self.assertContains(response, 'Programación I')
        self.assertContains(response, 'Tecnicatura en Desarrollo de Software')
        self.assertContains(response, '88%')
        self.assertContains(response, '9')  # Nota final

    def test_portal_docente_view_authenticated(self):
        self.client.login(username='25111222', password='123456789')
        response = self.client.get(reverse('portal:docente'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'López, Carlos')
        self.assertContains(response, 'Programación I')
        self.assertContains(response, 'COM-DS-1A')
        self.assertContains(response, 'Lic. en Sistemas')

    def test_cross_portal_isolation_alumno_blocked_from_docente(self):
        # Alumno intentando ingresar al portal docente es redirigido a su portal de alumno
        self.client.login(username='44333222', password='123456789')
        response = self.client.get(reverse('portal:docente'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('portal:alumno'))

    def test_cross_portal_isolation_docente_blocked_from_alumno(self):
        # Docente intentando ingresar al portal alumno es redirigido a su portal docente
        self.client.login(username='25111222', password='123456789')
        response = self.client.get(reverse('portal:alumno'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('portal:docente'))

    def test_alumno_and_docente_blocked_from_admin_modules(self):
        # Alumno bloqueado de buscador directivo
        self.client.login(username='44333222', password='123456789')
        resp_al = self.client.get(reverse('gestion:buscador'))
        self.assertEqual(resp_al.status_code, 302)
        self.assertRedirects(resp_al, reverse('portal:alumno'))

        # Docente bloqueado de carga de alumnos
        self.client.login(username='25111222', password='123456789')
        resp_doc = self.client.get(reverse('carga_alumnos:index'))
        self.assertEqual(resp_doc.status_code, 302)
        self.assertRedirects(resp_doc, reverse('portal:docente'))

    def test_idor_protection_imprimir_estado_academico(self):
        # Alumno solo puede imprimir su propio legajo/DNI
        self.client.login(username='44333222', password='123456789')
        # Su propio legajo: permitido
        resp_own = self.client.get(reverse('gestion:imprimir_estado_academico', kwargs={'dni': '44333222'}))
        self.assertEqual(resp_own.status_code, 200)

        # Legajo ajeno: bloqueado con 403
        resp_other = self.client.get(reverse('gestion:imprimir_estado_academico', kwargs={'dni': '25111222'}))
        self.assertEqual(resp_other.status_code, 403)
