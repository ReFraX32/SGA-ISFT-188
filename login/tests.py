from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from io import StringIO

class LoginAppTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='admin',
            password='mde123',
        )

    def test_login_view_renders_username_and_password_fields(self):
        response = self.client.get(reverse('login:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'Ingreso al Sistema')

    def test_valid_credentials_redirect_to_buscador(self):
        response = self.client.post(
            reverse('login:login'),
            {'username': 'admin', 'password': 'mde123'},
        )
        self.assertRedirects(response, reverse('gestion:buscador'))

    def test_invalid_credentials_shows_error(self):
        response = self.client.post(
            reverse('login:login'),
            {'username': 'admin', 'password': 'clave_incorrecta'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Usuario o contraseña incorrectos')

    @override_settings(LOGIN_MAX_ATTEMPTS=2, LOGIN_LOCKOUT_SECONDS=60)
    def test_repeated_failed_login_is_limited(self):
        login_url = reverse('login:login')
        self.client.post(login_url, {'username': 'admin', 'password': 'bad1'})
        self.client.post(login_url, {'username': 'admin', 'password': 'bad2'})
        response = self.client.post(login_url, {'username': 'admin', 'password': 'mde123'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Demasiados intentos fallidos')

    def test_logout_redirects_to_login(self):
        self.client.login(username='admin', password='mde123')
        response = self.client.get(reverse('login:logout'))
        self.assertRedirects(response, reverse('login:login'))

    def test_crear_usuario_admin_command(self):
        stdout = StringIO()
        call_command('crear_usuario_admin', stdout=stdout)
        user = get_user_model().objects.get(username='admin')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password('mde123'))
