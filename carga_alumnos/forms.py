import re
import datetime
from typing import Any
from django import forms
from django.core.validators import EmailValidator
from django.apps import apps
from .models import Alumno


def calcular_digito_cuil(cuil_limpio: str) -> int:
    """
    Calcula el dígito verificador esperado según el algoritmo Módulo 11 de ANSES / AFIP.
    """
    multiplicadores = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(cuil_limpio[i]) * multiplicadores[i] for i in range(10))
    resto = suma % 11

    if resto == 0:
        return 0
    elif resto == 1:
        prefijo = cuil_limpio[:2]
        if prefijo == '20':
            return 9
        elif prefijo == '27':
            return 4
        else:
            return int(cuil_limpio[10])
    else:
        return 11 - resto


def validar_algoritmo_cuil(cuil_limpio: str) -> bool:
    """
    Valida un número de CUIL argentino según el estándar de la ANSES / AFIP (Módulo 11).
    """
    if len(cuil_limpio) != 11 or not cuil_limpio.isdigit():
        return False

    prefijo = cuil_limpio[:2]
    if prefijo not in ['20', '23', '24', '27']:
        return False

    digito_esperado = calcular_digito_cuil(cuil_limpio)
    return int(cuil_limpio[10]) == digito_esperado


class AlumnoForm(forms.ModelForm):
    """
    Formulario para el Paso 1: Ingreso secuencial y validado de datos del alumno.
    Estandarizado bajo normativas oficiales de Argentina (RENAPER / ANSES) para estudiantes argentinos y extranjeros.
    """

    nacionalidad = forms.ChoiceField(
        choices=[('', '-- Seleccionar Nacionalidad --')] + list(Alumno.NACIONALIDAD_CHOICES),
        widget=forms.Select(attrs={
            'id': 'id_nacionalidad',
            'class': 'w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border transition-all shadow-sm',
            'required': 'required',
            'onchange': 'toggleOtraNacionalidad(this.value)',
        }),
        label='Nacionalidad',
        required=True,
    )

    nacionalidad_otra = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'id': 'id_nacionalidad_otra',
            'class': 'w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border transition-all shadow-sm',
            'placeholder': 'Escribí tu nacionalidad...',
            'list': 'lista-nacionalidades-mundo',
            'autocomplete': 'off',
        })
    )

    class Meta:
        model = Alumno
        fields = [
            'dni',
            'cuil',
            'apellido',
            'nombre',
            'fecha_nacimiento',
            'genero',
            'email',
            'telefono',
            'direccion',
            'localidad',
            'nacionalidad',
        ]
        labels = {
            'dni': 'DNI',
            'cuil': 'CUIL',
            'apellido': 'Apellido(s)',
            'nombre': 'Nombre(s)',
            'fecha_nacimiento': 'Fecha de Nacimiento',
            'genero': 'Identidad de Género',
            'email': 'Correo Electrónico',
            'telefono': 'Teléfono / Celular',
            'direccion': 'Dirección (Calle y Número)',
            'localidad': 'Localidad',
            'nacionalidad': 'Nacionalidad',
        }
        widgets = {
            'dni': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border transition-all shadow-sm',
                'placeholder': 'Ej. 38.123.456',
                'autocomplete': 'off',
                'required': 'required',
            }),
            'cuil': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border transition-all shadow-sm font-mono',
                'placeholder': 'Ej. 20-38123456-7',
                'autocomplete': 'off',
                'required': 'required',
            }),
            'apellido': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border transition-all shadow-sm',
                'placeholder': 'Apellido(s)',
                'autocomplete': 'family-name',
                'required': 'required',
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border transition-all shadow-sm',
                'placeholder': 'Nombre(s) completo(s)',
                'autocomplete': 'given-name',
                'required': 'required',
            }),
            'fecha_nacimiento': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border transition-all shadow-sm',
                'type': 'date',
                'required': 'required',
            }),
            'genero': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border transition-all shadow-sm',
                'required': 'required',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border transition-all shadow-sm',
                'placeholder': 'ejemplo@correo.com',
                'autocomplete': 'email',
                'required': 'required',
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border transition-all shadow-sm font-mono',
                'placeholder': 'Ej. +54 9 11 1234-5678 o internacional',
                'autocomplete': 'tel',
                'required': 'required',
            }),
            'direccion': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border transition-all shadow-sm',
                'placeholder': 'Calle, Número, Piso/Depto',
                'autocomplete': 'street-address',
                'required': 'required',
            }),
            'localidad': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border transition-all shadow-sm',
                'required': 'required',
            }),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'nacionalidad_otra':
                field.required = True
            if isinstance(field, forms.ChoiceField):
                if name == 'genero':
                    field.choices = [('', '-- Seleccionar Género --')] + list(Alumno.GENERO_CHOICES)
                elif name == 'localidad':
                    field.choices = [('', '-- Seleccionar Localidad --')] + list(Alumno.LOCALIDAD_CHOICES)
                elif name == 'nacionalidad':
                    field.choices = [('', '-- Seleccionar Nacionalidad --')] + list(Alumno.NACIONALIDAD_CHOICES)

        # Si el formulario está ligado (POST), permitir nacionalidades personalizadas en las opciones válidas
        if self.is_bound and 'nacionalidad' in self.fields:
            post_nac = self.data.get('nacionalidad')
            if post_nac and post_nac not in [opt[0] for opt in self.fields['nacionalidad'].choices]:
                self.fields['nacionalidad'].choices = list(self.fields['nacionalidad'].choices) + [(post_nac, post_nac)]

        # Si la nacionalidad inicial no está entre las opciones fijas, cargar en nacionalidad_otra
        val_nac = self.initial.get('nacionalidad')
        if val_nac and 'nacionalidad' in self.fields:
            opciones_nombres = [opt[0] for opt in Alumno.NACIONALIDAD_CHOICES]
            if val_nac not in opciones_nombres:
                self.fields['nacionalidad'].choices = list(self.fields['nacionalidad'].choices) + [(val_nac, val_nac)]
                self.initial['nacionalidad'] = 'Otra'
                self.initial['nacionalidad_otra'] = val_nac

    def is_valid(self) -> bool:
        """
        Sobrescribe is_valid para inyectar automáticamente clases de estilo de error en color rojo
        armónico a los campos con inconsistencias.
        """
        valid = super().is_valid()
        if not valid:
            for field_name in self.errors:
                if field_name in self.fields:
                    widget = self.fields[field_name].widget
                    classes = widget.attrs.get('class', '')
                    widget.attrs['class'] = (
                        classes.replace('theme-border', '').strip()
                        + ' !border-rose-500 !bg-rose-500/[0.08] focus:!border-rose-400 focus:!ring-2 focus:!ring-rose-500/30'
                    )
        return valid

    def clean_nacionalidad(self) -> str:
        nac = str(self.cleaned_data.get('nacionalidad', '')).strip()
        if not nac:
            raise forms.ValidationError("Por favor, seleccioná o escribí tu nacionalidad.")
        if nac == 'Otra':
            otra = str(self.data.get('nacionalidad_otra', '')).strip()
            if not otra:
                raise forms.ValidationError("Por favor, escribí tu nacionalidad en el campo de texto.")
            return otra.title()
        return nac

    def clean_dni(self) -> str:
        dni_raw = str(self.cleaned_data.get('dni', '')).strip()
        if not dni_raw:
            raise forms.ValidationError("Por favor, ingresá el número de DNI.")

        # Validación oficial RENAPER: el DNI solo contiene números (admite puntos o espacios de formato)
        if not re.match(r'^[\d\.\s]+$', dni_raw):
            raise forms.ValidationError("El DNI debe contener solo números.")

        dni_limpio = re.sub(r'[^\d]', '', dni_raw)
        if len(dni_limpio) < 7 or len(dni_limpio) > 8:
            raise forms.ValidationError("El DNI debe tener 7 u 8 números.")

        # Verificar unicidad en módulo carga_alumnos
        if Alumno.objects.filter(dni=dni_limpio).exists():
            raise forms.ValidationError(f"Ya existe un alumno registrado con este DNI ({dni_limpio}).")

        # Verificar unicidad en módulo gestión (si existe)
        try:
            if apps.is_installed('gestion'):
                PersonaModel = apps.get_model('gestion', 'Persona')
                if PersonaModel.objects.filter(dni=dni_limpio).exists():
                    raise forms.ValidationError(f"Ya existe una persona registrada en el sistema con este DNI ({dni_limpio}).")
        except forms.ValidationError:
            raise
        except Exception:
            pass

        return dni_limpio

    def clean_cuil(self) -> str:
        cuil_raw = str(self.cleaned_data.get('cuil', '')).strip()
        if not cuil_raw:
            raise forms.ValidationError("El número de CUIL es obligatorio.")

        # Validación oficial ANSES: solo números y guiones opcionales
        if not re.match(r'^[\d\-\s]+$', cuil_raw):
            raise forms.ValidationError("El CUIL debe contener solo números y guiones.")

        # Validación oficial ANSES (Módulo 11) para todos los alumnos (argentinos o extranjeros radicados)
        cuil_limpio = re.sub(r'[^\d]', '', cuil_raw)
        if len(cuil_limpio) != 11:
            raise forms.ValidationError("El CUIL debe tener exactamente 11 números.")

        prefijo = cuil_limpio[:2]
        if prefijo not in ['20', '23', '24', '27']:
            raise forms.ValidationError("El CUIL debe comenzar con 20, 23, 24 o 27.")

        dni_val = self.cleaned_data.get('dni', '')
        if dni_val:
            dni_digitos = re.sub(r'[^\d]', '', str(dni_val)).zfill(8)
            cuil_dni_part = cuil_limpio[2:10]
            if cuil_dni_part != dni_digitos:
                raise forms.ValidationError("Los números centrales del CUIL no coinciden con el DNI ingresado.")

        if not validar_algoritmo_cuil(cuil_limpio):
            raise forms.ValidationError("El número de CUIL no es correcto. Por favor, revisá que esté bien escrito.")

        cuil_formateado = f"{cuil_limpio[:2]}-{cuil_limpio[2:10]}-{cuil_limpio[10:]}"

        # Verificar unicidad
        if Alumno.objects.filter(cuil=cuil_formateado).exists() or Alumno.objects.filter(cuil=cuil_limpio).exists():
            raise forms.ValidationError(f"Ya existe un alumno registrado con este CUIL ({cuil_formateado}).")

        try:
            if apps.is_installed('gestion'):
                PersonaModel = apps.get_model('gestion', 'Persona')
                if PersonaModel.objects.filter(cuil=cuil_formateado).exists() or PersonaModel.objects.filter(cuil=cuil_limpio).exists():
                    raise forms.ValidationError(f"Ya existe una persona registrada en el sistema con este CUIL ({cuil_formateado}).")
        except forms.ValidationError:
            raise
        except Exception:
            pass

        return cuil_formateado

    def clean_nombre(self) -> str:
        nombre = str(self.cleaned_data.get('nombre', '')).strip()
        if not nombre or len(nombre) < 2:
            raise forms.ValidationError("Ingresá el nombre completo.")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s'\-]+$", nombre):
            raise forms.ValidationError("Ingresá solo letras en el nombre.")
        return nombre.title()

    def clean_apellido(self) -> str:
        apellido = str(self.cleaned_data.get('apellido', '')).strip()
        if not apellido or len(apellido) < 2:
            raise forms.ValidationError("Ingresá el apellido completo.")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s'\-]+$", apellido):
            raise forms.ValidationError("Ingresá solo letras en el apellido.")
        return apellido.title()

    def clean_fecha_nacimiento(self) -> datetime.date:
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if not fecha:
            raise forms.ValidationError("La fecha de nacimiento es obligatoria.")

        hoy = datetime.date.today()
        if fecha >= hoy:
            raise forms.ValidationError("La fecha de nacimiento no puede ser futura ni de hoy.")

        edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
        if edad < 15:
            raise forms.ValidationError("La edad mínima para ingresar es de 15 años.")
        if edad > 110:
            raise forms.ValidationError("Por favor, ingresá una fecha de nacimiento válida.")

        return fecha

    def clean_email(self) -> str:
        email = str(self.cleaned_data.get('email', '')).strip().lower()
        if not email:
            raise forms.ValidationError("El correo electrónico es obligatorio.")
        validator = EmailValidator(
            message="Ingresá un correo electrónico válido (ejemplo: usuario@correo.com)."
        )
        validator(email)
        return email

    def clean_telefono(self) -> str:
        tel = str(self.cleaned_data.get('telefono', '')).strip()
        if not tel:
            raise forms.ValidationError("El teléfono de contacto es obligatorio.")
        digitos = re.sub(r'[^\d]', '', tel)
        if len(digitos) < 7 or len(digitos) > 18:
            raise forms.ValidationError("Ingresá un teléfono válido (entre 7 y 18 números).")
        # Estándar internacional E.164: permite prefijo +, números, espacios, guiones
        if not re.match(r"^[\+]?[\d\s\-\(\)]{7,25}$", tel):
            raise forms.ValidationError("Ingresá un número de teléfono válido con código de área o país.")
        return tel

    def clean_direccion(self) -> str:
        direccion = str(self.cleaned_data.get('direccion', '')).strip()
        if not direccion or len(direccion) < 4:
            raise forms.ValidationError("Por favor, ingresá la calle y número de tu domicilio.")
        return direccion

    def clean_localidad(self) -> str:
        localidad = str(self.cleaned_data.get('localidad', '')).strip()
        if not localidad:
            raise forms.ValidationError("Por favor, seleccioná tu localidad.")
        return localidad

    def clean_genero(self) -> str:
        genero = str(self.cleaned_data.get('genero', '')).strip()
        if not genero:
            raise forms.ValidationError("Por favor, seleccioná una opción de género.")
        return genero
