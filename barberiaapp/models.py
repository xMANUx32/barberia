from django.db import models
from datetime import timedelta, datetime

class Cliente(models.Model):
    rut = models.CharField(max_length=12, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(max_length=254, unique=True)
    password = models.CharField(max_length=128)
    activo = models.BooleanField(default=True) 

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.rut}"


class Corte(models.Model):
    CATEGORIAS = [
        ('barba', 'Barba'),
        ('cabello', 'Cabello'),
        ('combo', 'Cabello + Barba'),
        ('premium', 'Otros'),
    ]
    
    categoria = models.CharField(max_length=20, choices=CATEGORIAS)
    titulo = models.CharField(max_length=100)
    duracion = models.PositiveIntegerField()
    precio = models.PositiveIntegerField()
    descripcion = models.TextField()

    def __str__(self):
        return self.titulo



class Barbero(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=255)
    cortes_destacados = models.TextField()
    especialidad = models.CharField(max_length=100)
    rut = models.CharField(max_length=12, unique=True)
    contraseña = models.CharField(max_length=100)
    disponible = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre
    

class Reserva(models.Model):
    ESTADOS_RESERVA = [
    ('pendiente', 'Pendiente'),
    ('realizada', 'Realizada'),
    ('cancelada', 'Cancelada'),
    ('no_asistio', 'No asistió'),
    ]
    corte = models.ForeignKey(Corte, on_delete=models.CASCADE)
    barbero = models.ForeignKey(Barbero, on_delete=models.CASCADE)
    nombre_cliente = models.CharField(max_length=100)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField(blank=True)
    editado = models.BooleanField(default=False)
    estado = models.CharField(max_length=20, choices=ESTADOS_RESERVA, default='pendiente')
   

    def save(self, *args, **kwargs):
        inicio = datetime.combine(self.fecha, self.hora_inicio)
        self.hora_fin = (inicio + timedelta(minutes=self.corte.duracion)).time()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre_cliente} - {self.corte.titulo} ({self.fecha} {self.hora_inicio})"
    
from django.contrib.auth.hashers import make_password, check_password

class Admin(models.Model):
    rut = models.CharField(max_length=12, unique=True)
    contraseña = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        if not self.contraseña.startswith('pbkdf2_'):  
            self.contraseña = make_password(self.contraseña)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.rut