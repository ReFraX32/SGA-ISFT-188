from django.conf import settings
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib.auth import logout

from .forms import LoginForm
from .security import clear_failed_logins, is_login_limited, lockout_seconds, register_failed_login


class LoginView(DjangoLoginView):
    authentication_form = LoginForm
    redirect_authenticated_user = True
    redirect_field_name = 'next'
    template_name = 'login/login.html'
    username_post_key = 'username'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'Acceso al Sistema — ISFT N° 188',
            'login_label': 'Autenticación Institucional',
            'login_heading': 'Ingreso al Sistema',
        })
        return context

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            username = request.POST.get(self.username_post_key, '')
            if is_login_limited(request, username):
                form_class = self.get_form_class()
                form = form_class(request=request, data=request.POST)
                minutos = lockout_seconds() // 60 or 1
                form.add_error(
                    None,
                    f'Demasiados intentos fallidos. Por favor, esperá {minutos} minuto(s) e intentá nuevamente.'
                )
                return self.form_invalid(form)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        clear_failed_logins(self.request, self.request.POST.get(self.username_post_key, ''))
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.method == 'POST':
            register_failed_login(
                self.request,
                self.request.POST.get(self.username_post_key, ''),
            )
        return super().form_invalid(form)


class LogoutView(DjangoLogoutView):
    http_method_names = ['get', 'post', 'options']
    next_page = reverse_lazy('login:login')

    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect(self.next_page)

    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect(self.next_page)
