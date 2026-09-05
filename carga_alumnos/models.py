from django.db import models
from django.core.validators import RegexValidator


class Alumno(models.Model):
    """
    Modelo representativo del Alumno para el módulo modular de Carga/Alta de Alumnos.
    Encapsulado de forma autónoma con sincronización a PostgreSQL / SGA.
    """

    GENERO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('I', 'Indistinto'),
        ('N', 'Prefiere no decir'),
    ]

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

    # Manager explícito para compatibilidad estática y tipado IDE
    objects = models.Manager()

    # Campos de Identificación Oficial según normativas oficiales de Argentina (RENAPER / ANSES)
    dni = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name="DNI",
        validators=[
            RegexValidator(
                regex=r'^\d{7,8}$',
                message='Ingrese un número de DNI válido de 7 u 8 dígitos.'
            )
        ]
    )
    cuil = models.CharField(
        max_length=20,
        blank=True,
        default="",
        db_index=True,
        verbose_name="CUIL",
        validators=[
            RegexValidator(
                regex=r'^\d{2}-\d{8}-\d{1}$|^\d{11}$',
                message='Ingrese un número de CUIL válido de 11 dígitos numéricos.'
            )
        ]
    )
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    apellido = models.CharField(max_length=100, verbose_name="Apellido")
    fecha_nacimiento = models.DateField(verbose_name="Fecha de Nacimiento")
    email = models.EmailField(max_length=254, verbose_name="Correo Electrónico")
    telefono = models.CharField(max_length=50, verbose_name="Teléfono")
    direccion = models.CharField(max_length=200, verbose_name="Dirección")

    # Campos con opciones
    genero = models.CharField(
        max_length=1,
        choices=GENERO_CHOICES,
        default='N',
        verbose_name="Género"
    )
    nacionalidad = models.CharField(
        max_length=100,
        default='Argentina',
        verbose_name="Nacionalidad"
    )
    localidad = models.CharField(
        max_length=100,
        choices=LOCALIDAD_CHOICES,
        default='General Rodríguez',
        verbose_name="Localidad"
    )

    # Auditoría
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")

    class Meta:
        db_table = 'carga_alumnos_alumno'
        verbose_name = "Alumno"
        verbose_name_plural = "Alumnos"
        ordering = ['-fecha_registro', 'apellido', 'nombre']

    def __str__(self) -> str:
        return f"{self.apellido}, {self.nombre} (DNI: {self.dni} | CUIL: {self.cuil})"
