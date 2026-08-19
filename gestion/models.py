import datetime
from django.db import models

class Persona(models.Model):
    GENERO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('O', 'Otro'),
        ('N', 'Prefiere no decir'),
    ]

    id_persona = models.AutoField(primary_key=True, verbose_name="ID Persona")
    cuil = models.CharField(max_length=20, blank=True, null=True, db_index=True, verbose_name="CUIL")
    dni = models.CharField(max_length=20, unique=True, db_index=True, verbose_name="DNI")
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    apellido = models.CharField(max_length=100, verbose_name="Apellido")
    domicilio = models.CharField(max_length=200, blank=True, null=True, verbose_name="Domicilio")
    localidad = models.CharField(max_length=100, blank=True, null=True, db_index=True, verbose_name="Localidad")
    telefono = models.CharField(max_length=50, blank=True, null=True, verbose_name="Teléfono / Celular")
    mail = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    nacionalidad = models.CharField(max_length=100, blank=True, null=True, default="Argentina", verbose_name="Nacionalidad")
    fecha_nacimiento = models.DateField(blank=True, null=True, verbose_name="Fecha de Nacimiento")
    identidad = models.CharField(max_length=1, choices=GENERO_CHOICES, default='N', db_index=True, verbose_name="Identidad de Género")

    class Meta:
        verbose_name = "Persona"
        verbose_name_plural = "Personas"
        ordering = ['apellido', 'nombre']

    def __str__(self):
        return f"{self.apellido}, {self.nombre} (DNI: {self.dni})"

    @property
    def edad(self):
        """
        Cálculo dinámico de la edad a partir de la fecha de nacimiento (ISO 8601).
        No se almacena físicamente en la base de datos para evitar inconsistencias temporales.
        """
        if not self.fecha_nacimiento:
            return None
        today = datetime.date.today()
        return today.year - self.fecha_nacimiento.year - (
            (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )

    @property
    def genero_descripcion(self):
        return dict(self.GENERO_CHOICES).get(self.identidad, 'Prefiere no decir')


class Alumno(models.Model):
    persona = models.OneToOneField(Persona, on_delete=models.CASCADE, primary_key=True, related_name='alumno_profile')
    legajo = models.CharField(max_length=50, blank=True, null=True, db_index=True, verbose_name="N° Legajo")

    class Meta:
        verbose_name = "Alumno"
        verbose_name_plural = "Alumnos"

    def __str__(self):
        return f"Alumno: {self.persona.apellido}, {self.persona.nombre}"


class Docente(models.Model):
    persona = models.OneToOneField(Persona, on_delete=models.CASCADE, primary_key=True, related_name='docente_profile')
    titulo_mn = models.CharField(max_length=150, blank=True, null=True, verbose_name="Título / Matrícula Nacional")

    class Meta:
        verbose_name = "Docente"
        verbose_name_plural = "Docentes"

    def __str__(self):
        return f"Prof. {self.persona.apellido}, {self.persona.nombre}"


class Carrera(models.Model):
    codigo_carrera = models.CharField(max_length=50, primary_key=True, verbose_name="Código Carrera")
    nombre_carrera = models.CharField(max_length=200, verbose_name="Nombre de la Carrera")
    resolucion_vigente = models.CharField(max_length=100, blank=True, null=True, verbose_name="Resolución Vigente")
    resolucion_anterior = models.CharField(max_length=100, blank=True, null=True, verbose_name="Resolución Anterior")

    class Meta:
        verbose_name = "Carrera"
        verbose_name_plural = "Carreras"
        ordering = ['nombre_carrera']

    def __str__(self):
        return f"{self.nombre_carrera} ({self.resolucion_vigente or 'Sin Res.'})"


class Materia(models.Model):
    codigo_materia = models.CharField(max_length=50, primary_key=True, verbose_name="Código Materia")
    nombre_materia = models.CharField(max_length=200, verbose_name="Nombre de la Materia")

    class Meta:
        verbose_name = "Materia"
        verbose_name_plural = "Materias"
        ordering = ['nombre_materia']

    def __str__(self):
        return f"{self.codigo_materia} - {self.nombre_materia}"


class PlanEstudio(models.Model):
    id_plan = models.AutoField(primary_key=True, verbose_name="ID Plan")
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name='planes_estudio', db_column='codigo_carrera')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='planes_estudio', db_column='codigo_materia')
    anio_carrera = models.IntegerField(default=1, verbose_name="Año de Carrera")
    modalidad = models.CharField(max_length=50, default="Anual", verbose_name="Modalidad")
    carga_horaria_anual = models.IntegerField(blank=True, null=True, verbose_name="Carga Horaria Anual")
    carga_horaria_semanal = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, verbose_name="Carga Horaria Semanal")
    correlatividades = models.CharField(max_length=200, blank=True, default="", verbose_name="Correlatividades")

    class Meta:
        verbose_name = "Plan de Estudio"
        verbose_name_plural = "Planes de Estudio"
        ordering = ['carrera', 'anio_carrera', 'materia']

    def __str__(self):
        return f"{self.carrera.nombre_carrera} - {self.anio_carrera}° Año: {self.materia.nombre_materia}"


class Comision(models.Model):
    codigo_comision = models.CharField(max_length=50, primary_key=True, verbose_name="Código Comisión")
    plan_estudio = models.ForeignKey(PlanEstudio, on_delete=models.CASCADE, related_name='comisiones', db_column='id_plan')
    anio_lectivo = models.IntegerField(default=2026, verbose_name="Año Lectivo")
    cuatrimestre = models.CharField(max_length=20, default="Anual", verbose_name="Cuatrimestre")
    turno = models.CharField(max_length=20, default="Vespertino", verbose_name="Turno")
    division = models.CharField(max_length=10, default="A", verbose_name="División")

    class Meta:
        verbose_name = "Comisión"
        verbose_name_plural = "Comisiones"
        ordering = ['anio_lectivo', 'codigo_comision']

    def __str__(self):
        return f"Comisión {self.codigo_comision} ({self.plan_estudio.materia.nombre_materia})"


class ComisionDocente(models.Model):
    comision = models.ForeignKey(Comision, on_delete=models.CASCADE, related_name='docentes_asignados', db_column='codigo_comision')
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE, related_name='comisiones_asignadas', db_column='id_persona_docente')
    rol = models.CharField(max_length=50, default="Titular", verbose_name="Rol Docente")

    class Meta:
        verbose_name = "Docente en Comisión"
        verbose_name_plural = "Docentes en Comisiones"
        unique_together = ('comision', 'docente')

    def __str__(self):
        return f"{self.docente} en {self.comision} ({self.rol})"


class Cursada(models.Model):
    SITUACIONES = [
        ('Promocionado', 'Promocionado'),
        ('Final', 'A Final'),
        ('Regular', 'Regular'),
        ('Libre', 'Libre / Recursa'),
        ('En Cursada', 'En Cursada'),
    ]

    id_cursada = models.AutoField(primary_key=True, verbose_name="ID Cursada")
    comision = models.ForeignKey(Comision, on_delete=models.CASCADE, related_name='cursadas', db_column='codigo_comision')
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name='cursadas', db_column='id_persona_alumno')
    porcentaje_asistencia = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="% Asistencia")
    situacion_final = models.CharField(max_length=50, choices=SITUACIONES, default='Regular', verbose_name="Situación Final")

    class Meta:
        verbose_name = "Cursada"
        verbose_name_plural = "Cursadas"
        unique_together = ('comision', 'alumno')

    def __str__(self):
        return f"{self.alumno.persona.apellido} - {self.comision.plan_estudio.materia.nombre_materia} ({self.situacion_final})"


class Evaluacion(models.Model):
    codigo_evaluacion = models.AutoField(primary_key=True, verbose_name="Código Evaluación")
    cursada = models.ForeignKey(Cursada, on_delete=models.CASCADE, related_name='evaluaciones', db_column='id_cursada')
    instancia = models.CharField(max_length=50, verbose_name="Instancia (Ej: Parcial 1, Recup, Nota Final)")
    nota = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name="Nota")
    fecha = models.DateField(null=True, blank=True, verbose_name="Fecha")

    class Meta:
        verbose_name = "Evaluación"
        verbose_name_plural = "Evaluaciones"

    def __str__(self):
        return f"{self.cursada.alumno.persona.apellido} - {self.instancia}: {self.nota}"
