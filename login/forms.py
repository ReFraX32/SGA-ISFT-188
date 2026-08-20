from django import forms
from django.contrib.auth.forms import AuthenticationForm, UsernameField


class LoginForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'Usuario o contraseña incorrectos. Por favor, verificá tus datos.',
        'inactive': 'Esta cuenta no está habilitada.',
    }

    username = UsernameField(
        label='Usuario',
        widget=forms.TextInput(
            attrs={
                'autofocus': True,
                'autocomplete': 'username',
                'class': (
                    'w-full rounded-xl pl-11 pr-4 py-3 text-sm font-semibold '
                    'shadow-inner focus:ring-2 focus:ring-indigo-500'
                ),
                'placeholder': 'Ingresá tu usuario',
            }
        ),
    )
    password = forms.CharField(
        label='Contraseña',
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'autocomplete': 'current-password',
                'class': (
                    'w-full rounded-xl pl-11 pr-12 py-3 text-sm font-semibold '
                    'shadow-inner focus:ring-2 focus:ring-indigo-500'
                ),
                'placeholder': 'Ingresá tu contraseña',
            }
        ),
    )
