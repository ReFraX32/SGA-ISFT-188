import re
from typing import Any
from django import forms
from django.core.exceptions import ValidationError
from gestion.models import Carrera

INPUT_CLASS = (
    "w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border "
    "transition-all shadow-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20"
)
SELECT_CLASS = (
    "w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border "
    "transition-all shadow-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 cursor-pointer"
)


class CarreraForm(forms.ModelForm):
    duracion_anios = forms.IntegerField(
        min_value=1,
        max_value=6,
        initial=3,
        label="Años de Cursada",
        widget=forms.Select(
            choices=[
                (1, "1 Año"),
                (2, "2 Años"),
                (3, "3 Años (Tecnicatura Estándar)"),
                (4, "4 Años"),
                (5, "5 Años"),
                (6, "6 Años"),
            ],
            attrs={'class': SELECT_CLASS}
        )
    )

    class Meta:
        model = Carrera
        fields = ['codigo_carrera', 'nombre_carrera', 'resolucion_vigente', 'resolucion_anterior']
        labels = {
            'codigo_carrera': 'Código Identificador de la Carrera',
            'nombre_carrera': 'Nombre Oficial de la Carrera',
            'resolucion_vigente': 'Resolución Ministerial Vigente',
            'resolucion_anterior': 'Resolución Anterior (Opcional)',
        }
        widgets = {
            'codigo_carrera': forms.TextInput(attrs={
                'class': INPUT_CLASS + ' font-mono uppercase',
                'placeholder': 'Ej. DESARROLLO-SOFTWARE-188',
                'autocomplete': 'off',
            }),
            'nombre_carrera': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Ej. Tecnicatura Superior en Desarrollo de Software',
                'autocomplete': 'off',
            }),
            'resolucion_vigente': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Ej. Res. N° 6183/19',
                'autocomplete': 'off',
            }),
            'resolucion_anterior': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Ej. Res. N° 320/09 (opcional si hubo plan previo)',
                'autocomplete': 'off',
            }),
        }

    def clean_codigo_carrera(self) -> str:
        codigo = str(self.cleaned_data.get('codigo_carrera', '')).strip().upper()
        if not codigo:
            raise ValidationError("El código de carrera es obligatorio.")
        if len(codigo) < 3:
            raise ValidationError("El código debe tener al menos 3 caracteres.")
        if not re.match(r"^[A-Z0-9_\-]+$", codigo):
            raise ValidationError("El código solo puede contener letras mayúsculas, números, guiones y guiones bajos (sin espacios ni acentos).")
        if Carrera.objects.filter(codigo_carrera=codigo).exists():
            raise ValidationError(f"Ya existe una carrera registrada con el código '{codigo}'. Elegí un código diferente.")
        return codigo

    def clean_nombre_carrera(self) -> str:
        nombre = str(self.cleaned_data.get('nombre_carrera', '')).strip()
        if not nombre or len(nombre) < 4:
            raise ValidationError("Ingresá el nombre completo oficial de la carrera (mínimo 4 caracteres).")
        return nombre


class CarreraEditForm(forms.ModelForm):
    class Meta:
        model = Carrera
        fields = ['nombre_carrera', 'resolucion_vigente', 'resolucion_anterior']
        labels = {
            'nombre_carrera': 'Nombre de la Carrera',
            'resolucion_vigente': 'Resolución Vigente',
            'resolucion_anterior': 'Resolución Anterior',
        }
        widgets = {
            'nombre_carrera': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'resolucion_vigente': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'resolucion_anterior': forms.TextInput(attrs={'class': INPUT_CLASS}),
        }

    def clean_nombre_carrera(self) -> str:
        nombre = str(self.cleaned_data.get('nombre_carrera', '')).strip()
        if not nombre or len(nombre) < 4:
            raise ValidationError("Ingresá el nombre completo oficial de la carrera (mínimo 4 caracteres).")
        return nombre
