import re
import datetime
from typing import Any, Optional
from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError

from gestion.models import Persona, Alumno, Docente
from gestion.validaciones import validar_cuil_detallado


INPUT_CLASS = (
    "w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border "
    "transition-all shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
)
SELECT_CLASS = (
    "w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border "
    "transition-all shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 cursor-pointer"
)


class PersonaBaseForm(forms.ModelForm):
    """
    Formulario base modular para datos personales (Persona).
    Compartido y reutilizado entre Alumnos y Docentes.
    """

    class Meta:
        model = Persona
        fields = [
            'dni',
            'cuil',
            'nombre',
            'apellido',
            'fecha_nacimiento',
            'identidad',
            'nacionalidad',
            'localidad',
            'domicilio',
            'telefono',
            'mail',
        ]
        widgets = {
            'dni': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. 38123456', 'autocomplete': 'off'}),
            'cuil': forms.TextInput(attrs={'class': INPUT_CLASS + ' font-mono', 'placeholder': 'Ej. 20-38123456-7', 'autocomplete': 'off'}),
            'nombre': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Nombres'}),
            'apellido': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Apellidos'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'}),
            'identidad': forms.Select(attrs={'class': SELECT_CLASS}),
            'nacionalidad': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. Argentina'}),
            'localidad': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. General Rodríguez'}),
            'domicilio': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Calle, número, piso/depto'}),
            'telefono': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. +54 9 11 1234-5678'}),
            'mail': forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'correo@ejemplo.com'}),
        }

    def clean_dni(self) -> str:
        dni_raw = str(self.cleaned_data.get('dni', '')).strip()
        if not dni_raw:
            raise ValidationError("El DNI es obligatorio.")

        dni_limpio = re.sub(r'[^\d]', '', dni_raw)
        if len(dni_limpio) < 6 or len(dni_limpio) > 9:
            raise ValidationError("El DNI debe tener entre 6 y 9 dígitos numéricos.")

        qs = Persona.objects.filter(dni=dni_limpio)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"Ya existe una persona registrada en el sistema con este DNI ({dni_limpio}).")

        return dni_limpio

    def clean_cuil(self) -> str:
        cuil_raw = str(self.cleaned_data.get('cuil', '')).strip()
        dni_val = self.cleaned_data.get('dni', '')

        cuil_formateado, error_msg = validar_cuil_detallado(cuil_raw, dni_val=dni_val)
        if error_msg:
            raise ValidationError(error_msg)

        cuil_limpio = re.sub(r'[^\d]', '', cuil_formateado)
        qs = Persona.objects.filter(cuil__in=[cuil_formateado, cuil_limpio])
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"Ya existe una persona registrada en el sistema con este CUIL ({cuil_formateado}).")

        return cuil_formateado

    def clean_nombre(self) -> str:
        nombre = str(self.cleaned_data.get('nombre', '')).strip()
        if not nombre or len(nombre) < 2:
            raise ValidationError("Ingresá el nombre completo.")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s'\-]+$", nombre):
            raise ValidationError("Ingresá solo letras en el nombre.")
        return nombre.title()

    def clean_apellido(self) -> str:
        apellido = str(self.cleaned_data.get('apellido', '')).strip()
        if not apellido or len(apellido) < 2:
            raise ValidationError("Ingresá el apellido completo.")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s'\-]+$", apellido):
            raise ValidationError("Ingresá solo letras en el apellido.")
        return apellido.title()

    def clean_fecha_nacimiento(self) -> Optional[datetime.date]:
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if not fecha:
            return None
        hoy = datetime.date.today()
        edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
        if edad < 15:
            raise ValidationError("La edad mínima para registrarse es de 15 años.")
        if edad > 110:
            raise ValidationError("La fecha de nacimiento ingresada no parece válida.")
        return fecha


class AlumnoEditForm(PersonaBaseForm):
    """
    Formulario para edición de Alumnos. Reutiliza la base de Persona
    y gestiona el campo específico 'legajo'.
    """
    legajo = forms.CharField(
        max_length=50,
        required=False,
        label="N° Legajo",
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. LEG-12345'})
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            try:
                alumno_profile = getattr(self.instance, 'alumno_profile', None)
                if alumno_profile and alumno_profile.legajo:
                    self.fields['legajo'].initial = alumno_profile.legajo
            except Exception:
                pass

    def save(self, commit: bool = True) -> Persona:
        persona = super().save(commit=commit)
        legajo_val = self.cleaned_data.get('legajo', '').strip()
        if commit:
            Alumno.objects.update_or_create(
                persona=persona,
                defaults={'legajo': legajo_val or f"LEG-{persona.dni}"}
            )

            # Sincronización con carga_alumnos si está instalado
            if apps.is_installed('carga_alumnos'):
                try:
                    AlumnoCarga = apps.get_model('carga_alumnos', 'Alumno')
                    AlumnoCarga.objects.filter(dni=persona.dni).update(
                        cuil=persona.cuil or "",
                        nombre=persona.nombre,
                        apellido=persona.apellido,
                        fecha_nacimiento=persona.fecha_nacimiento or datetime.date(2000, 1, 1),
                        genero=persona.identidad,
                        nacionalidad=persona.nacionalidad or "Argentina",
                        localidad=persona.localidad or "General Rodríguez",
                        direccion=persona.domicilio or "",
                        telefono=persona.telefono or "",
                        email=persona.mail or "",
                    )
                except Exception:
                    pass

        return persona


NACIONALIDAD_CHOICES = [
    ('Argentina', 'Argentina'),
    ('Boliviana', 'Boliviana'),
    ('Brasileña', 'Brasileña'),
    ('Chilena', 'Chilena'),
    ('Colombiana', 'Colombiana'),
    ('Ecuatoriana', 'Ecuatoriana'),
    ('Española', 'Española'),
    ('Italiana', 'Italiana'),
    ('Paraguaya', 'Paraguaya'),
    ('Peruana', 'Peruana'),
    ('Uruguaya', 'Uruguaya'),
    ('Venezolana', 'Venezolana'),
    ('Otra', 'Otra'),
]

LOCALIDAD_CHOICES = [
    ('General Rodríguez', 'General Rodríguez'),
    ('Moreno', 'Moreno'),
    ('Luján', 'Luján'),
    ('Pilar', 'Pilar'),
    ('Mercedes', 'Mercedes'),
    ('San Miguel', 'San Miguel'),
    ('Marcos Paz', 'Marcos Paz'),
    ('Merlo', 'Merlo'),
    ('Morón', 'Morón'),
    ('Ituzaingó', 'Ituzaingó'),
    ('Hurlingham', 'Hurlingham'),
    ('José C. Paz', 'José C. Paz'),
    ('Malvinas Argentinas', 'Malvinas Argentinas'),
    ('Jáuregui', 'Jáuregui'),
    ('Navarro', 'Navarro'),
    ('CABA', 'CABA (Ciudad Autónoma de Buenos Aires)'),
    ('Otra Localidad', 'Otra Localidad'),
]


class DocenteForm(PersonaBaseForm):
    """
    Formulario unificado para Alta y Edición de Docentes.
    Reutiliza la base de Persona y gestiona 'titulo_mn', 'nacionalidad' y 'localidad'.
    """
    nacionalidad = forms.ChoiceField(
        choices=[('', '-- Seleccionar Nacionalidad --')] + NACIONALIDAD_CHOICES,
        widget=forms.Select(attrs={
            'id': 'id_nacionalidad',
            'class': SELECT_CLASS,
            'onchange': 'toggleOtraNacionalidad(this.value)',
        }),
        label='Nacionalidad',
        required=False,
    )
    nacionalidad_otra = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'id': 'id_nacionalidad_otra',
            'class': INPUT_CLASS,
            'placeholder': 'Escribí la nacionalidad...',
            'list': 'lista-nacionalidades-mundo',
            'autocomplete': 'off',
        })
    )
    localidad = forms.ChoiceField(
        choices=[('', '-- Seleccionar Localidad --')] + LOCALIDAD_CHOICES,
        widget=forms.Select(attrs={
            'id': 'id_localidad',
            'class': SELECT_CLASS,
        }),
        label='Localidad',
        required=False,
    )
    titulo_mn = forms.CharField(
        max_length=150,
        required=False,
        label="Título / Matrícula Nacional",
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. Prof. en Informática / MN 12345'})
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            try:
                docente_profile = getattr(self.instance, 'docente_profile', None)
                if docente_profile and docente_profile.titulo_mn:
                    self.fields['titulo_mn'].initial = docente_profile.titulo_mn
            except Exception:
                pass

        if self.is_bound and 'nacionalidad' in self.fields:
            post_nac = self.data.get('nacionalidad')
            if post_nac and post_nac not in [opt[0] for opt in self.fields['nacionalidad'].choices]:
                self.fields['nacionalidad'].choices = list(self.fields['nacionalidad'].choices) + [(post_nac, post_nac)]

        val_nac = self.initial.get('nacionalidad')
        if val_nac and 'nacionalidad' in self.fields:
            opciones_nombres = [opt[0] for opt in NACIONALIDAD_CHOICES]
            if val_nac not in opciones_nombres:
                self.fields['nacionalidad'].choices = list(self.fields['nacionalidad'].choices) + [(val_nac, val_nac)]
                self.initial['nacionalidad'] = 'Otra'
                self.initial['nacionalidad_otra'] = val_nac

        if self.is_bound and 'localidad' in self.fields:
            post_loc = self.data.get('localidad')
            if post_loc and post_loc not in [opt[0] for opt in self.fields['localidad'].choices]:
                self.fields['localidad'].choices = list(self.fields['localidad'].choices) + [(post_loc, post_loc)]

        val_loc = self.initial.get('localidad')
        if val_loc and 'localidad' in self.fields:
            opciones_loc = [opt[0] for opt in LOCALIDAD_CHOICES]
            if val_loc not in opciones_loc:
                self.fields['localidad'].choices = list(self.fields['localidad'].choices) + [(val_loc, val_loc)]

    def clean_nacionalidad(self) -> str:
        nac = str(self.cleaned_data.get('nacionalidad', '')).strip()
        if nac == 'Otra':
            otra = str(self.data.get('nacionalidad_otra', '')).strip()
            return otra.title() if otra else ''
        return nac

    def save(self, commit: bool = True) -> Persona:
        persona = super().save(commit=commit)
        titulo_val = self.cleaned_data.get('titulo_mn', '').strip()
        if commit:
            Docente.objects.update_or_create(
                persona=persona,
                defaults={'titulo_mn': titulo_val or None}
            )
        return persona

