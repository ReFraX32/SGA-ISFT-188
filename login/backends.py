import re
from typing import Optional
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.http import HttpRequest
from gestion.models import Persona, Alumno, Docente

DEFAULT_PORTAL_PASSWORD = '123456789'


class DNIAuthBackend(ModelBackend):
    """
    Backend de autenticación que permite a Alumnos y Docentes ingresar
    utilizando su número de DNI como identificador y su contraseña (inicialmente 123456789).
    Si se trata de un usuario administrativo tradicional (ej. admin), delega a ModelBackend.
    """

    def authenticate(self, request: Optional[HttpRequest], username: Optional[str] = None, password: Optional[str] = None, **kwargs) -> Optional[User]:
        if not username or not password:
            return None

        # 1. Intentar limpiar DNI si contiene caracteres como puntos o espacios
        dni_candidato = re.sub(r'[^\d]', '', str(username).strip())

        persona = None
        if dni_candidato:
            persona = Persona.objects.filter(dni=dni_candidato).first()

        # Si no se encontró por DNI limpio, intentar con el username tal cual
        if not persona:
            persona = Persona.objects.filter(dni=str(username).strip()).first()

        if persona:
            # Verificar si la persona es Alumno o Docente
            es_alumno = Alumno.objects.filter(persona=persona).exists()
            es_docente = Docente.objects.filter(persona=persona).exists()

            if es_alumno or es_docente:
                dni_oficial = persona.dni
                # Obtener o aprovisionar el usuario de Django para este DNI
                user = User.objects.filter(username=dni_oficial).first()
                if not user:
                    user = User(
                        username=dni_oficial,
                        first_name=(persona.nombre or '')[:150],
                        last_name=(persona.apellido or '')[:150],
                        email=(persona.mail or '')[:254],
                        is_staff=False,
                        is_superuser=False,
                        is_active=True,
                    )
                    user.set_password(DEFAULT_PORTAL_PASSWORD)
                    user.save()
                else:
                    # Si el usuario existe pero no tiene contraseña usable, asignarle la default
                    if not user.has_usable_password():
                        user.set_password(DEFAULT_PORTAL_PASSWORD)
                        user.save()

                if user.check_password(password) and self.user_can_authenticate(user):
                    return user

        # 2. Si no es alumno/docente o falló contraseña de portal, autenticar contra User estándar (ej: admin)
        return super().authenticate(request, username=username, password=password, **kwargs)
