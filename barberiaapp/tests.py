from django.test import TestCase

# Create your tests here.

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from django.contrib.messages import get_messages
from .models import Cliente, Reserva, Corte, Barbero
from django.utils import timezone
from datetime import timedelta, datetime
from .views import horarios_disponibles
import time

class LoginClienteTestCase(TestCase):
    def setUp(self):
        self.rut = '12345678-9'
        self.password = 'claveSegura123'
        self.email = 'cliente@ejemplo.com'

        self.cliente = Cliente.objects.create(
            rut=self.rut,
            first_name='Juan',
            last_name='Pérez',
            email=self.email,
            password=make_password(self.password),
            activo=True
        )

        self.login_url = reverse('login')

    def test_01_login_correcto_cliente_activo(self):
        print("\n🧩 Probando login correcto con cliente activo...")
        response = self.client.post(self.login_url, {
        'username': self.rut,
        'password': self.password
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('index'))
        session = self.client.session
        self.assertEqual(session['cliente_id'], self.cliente.id)
        time.sleep(3)
        print("✅ Login correcto: redirige a index y guarda sesión de cliente.")

    def test_02_login_incorrecto(self):
        print("\n🚫 Probando login con contraseña incorrecta...")
        response = self.client.post(self.login_url, {
            'username': self.rut,
            'password': 'claveErronea'
        }, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'barberiaapp/registro/login.html')

        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Contraseña incorrecta.", messages)

        self.assertNotIn('cliente_id', self.client.session)
        time.sleep(3)
        print("⚠️ Mensaje mostrado correctamente: 'Contraseña incorrecta.'")

    def test_03_login_cliente_inactivo(self):
        print("\n🔒 Probando login con cliente inactivo...")
        self.cliente.activo = False
        self.cliente.save()

        response = self.client.post(self.login_url, {
            'username': self.rut,
            'password': self.password
        }, follow=True)


        self.assertEqual(response.status_code, 200)
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Tu cuenta ha sido bloqueada por el administrador.", messages)
        self.assertNotIn('cliente_id', self.client.session)
        time.sleep(3)
        print("🚫 Cliente inactivo bloqueado correctamente.")



class ReservaClienteTest(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create(
            rut="12345678-9",
            first_name="Juan",
            last_name="Pérez",
            email="juan@example.com",
            password=make_password("clave123"),
            activo=True
        )

        self.barbero = Barbero.objects.create(
            nombre='Carlos',
            descripcion='Barbero experto',
            cortes_destacados='Corte clásico',
            especialidad='Cabello',
            rut='22.222.222-2',
            contraseña=make_password('1234'),
            disponible=True
        )

        self.corte = Corte.objects.create(
            categoria="cabello",
            titulo="Corte Clásico",
            duracion=30,
            precio=8000,
            descripcion="Corte clásico con terminación limpia"
        )

        self.client = Client()
        self.client.get('/')  
        session = self.client.session
        session['cliente_id'] = self.cliente.id
        session['cliente_nombre'] = self.cliente.first_name
        session.save()

    def test_04_cliente_puede_realizar_reserva(self):
        """Prueba completa del flujo de reserva de un cliente."""

        fecha_reserva = (timezone.now() + timedelta(days=1)).date()

        horas_disponibles = horarios_disponibles(
            fecha_reserva, 
            self.corte.duracion, 
            self.barbero.id
        )

        self.assertTrue(horas_disponibles, "❌ No hay horas disponibles para el test.")

        hora_inicio = horas_disponibles[0].strftime("%H:%M")  # tomar la primera hora libre

        data = {
            'corte': self.corte.id,
            'barbero': self.barbero.id,
            'fecha': fecha_reserva,
            'hora_inicio': hora_inicio,
        }

        response = self.client.post(reverse('reservas'), data, follow=True)

        self.assertIn(response.status_code, [200, 302], "❌ El servidor no respondió correctamente al crear la reserva.")

        reserva_existente = Reserva.objects.filter(
            nombre_cliente__icontains=self.cliente.first_name,
            corte=self.corte,
            barbero=self.barbero
        ).exists()

        self.assertTrue(reserva_existente, "❌ No se registró la reserva en la base de datos.")

        self.assertContains(response, "Reserva creada", msg_prefix="⚠️ No se muestra el mensaje de confirmación de reserva.")

        self.assertNotContains(response, "Error", msg_prefix="⚠️ El sistema muestra errores al reservar.")
        time.sleep(3)

        print("\n✅ Test completado: El cliente pudo realizar la reserva correctamente sin errores.")


class CancelarReservaTest(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create(
            rut="98765432-1",
            first_name="Pedro",
            last_name="Gómez",
            email="pedro@example.com",
            password=make_password("clave123"),
            activo=True
        )

        self.barbero = Barbero.objects.create(
            nombre='Luis',
            descripcion='Barbero profesional',
            cortes_destacados='Fade y clásico',
            especialidad='Cabello',
            rut='11.111.111-1',
            contraseña=make_password('1234'),
            disponible=True
        )

        self.corte = Corte.objects.create(
            categoria="cabello",
            titulo="Corte Fade",
            duracion=30,
            precio=10000,
            descripcion="Corte moderno con degradado."
        )

        self.fecha_reserva = (timezone.now() + timedelta(days=1)).date()
        self.hora_inicio = datetime.strptime("10:00", "%H:%M").time()


        self.reserva = Reserva.objects.create(
            nombre_cliente=f"{self.cliente.first_name} {self.cliente.last_name}",
            barbero=self.barbero,
            corte=self.corte,
            fecha=self.fecha_reserva,
            hora_inicio=self.hora_inicio,
            hora_fin=(datetime.combine(self.fecha_reserva, self.hora_inicio) + timedelta(minutes=30)).time(),
            estado='pendiente'
        )

        # Crear cliente HTTP y sesión activa
        self.client = Client()
        self.client.get('/')
        session = self.client.session
        session['cliente_id'] = self.cliente.id
        session['cliente_nombre'] = self.cliente.first_name
        session.save()

    def test_05_cliente_puede_cancelar_reserva_y_liberar_cupo(self):

        self.assertEqual(self.reserva.estado, 'pendiente', "❌ La reserva inicial no está en estado pendiente.")

        response = self.client.post(reverse('mis_reservas'), {
            'accion': 'cancelar',
            'reserva_id': self.reserva.id
        }, follow=True)

        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, 'cancelada', "❌ La reserva no se canceló correctamente en la base de datos.")

        self.assertIn(response.status_code, [200, 302], "❌ Error al procesar la cancelación.")

        self.assertContains(response, "cancelada exitosamente", msg_prefix="⚠️ No se muestra el mensaje de confirmación de cancelación.")

        api_url = f"{reverse('api_horas_disponibles')}?corte={self.corte.id}&fecha={self.fecha_reserva}&barbero={self.barbero.id}"
        api_response = self.client.get(api_url)
        self.assertEqual(api_response.status_code, 200, "❌ Error al consultar las horas disponibles.")

        horas_disponibles = api_response.json()
        hora_str = self.hora_inicio.strftime("%H:%M")
        self.assertIn(hora_str, horas_disponibles, f"❌ La hora {hora_str} no fue liberada correctamente en el calendario.")

        time.sleep(3)

        print("\n✅ Test completado: El cliente canceló su reserva y el cupo se liberó correctamente.")