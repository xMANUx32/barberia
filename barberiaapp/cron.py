from datetime import datetime, timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django_cron import CronJobBase, Schedule
from .models import Reserva, Cliente

def enviar_recordatorios():
    ahora = timezone.localtime()
    limite_inicio = ahora
    limite_fin = ahora + timedelta(minutes=2)  # Para pruebas inmediatas

    reservas = Reserva.objects.filter(
        estado='pendiente',
        fecha=limite_inicio.date()
    )

    for reserva in reservas:
        hora_reserva = datetime.combine(reserva.fecha, reserva.hora_inicio)
        hora_reserva = timezone.make_aware(hora_reserva)

        if limite_inicio <= hora_reserva <= limite_fin:
            try:
                nombre_partes = reserva.nombre_cliente.split()
                cliente = Cliente.objects.filter(first_name=nombre_partes[0]).first()

                if not cliente:
                    print(f"⚠️ Cliente no encontrado para la reserva ID {reserva.id}")
                    continue

                asunto = "⏰ Recordatorio de tu Reserva - Blessed Barbershop"
                mensaje = (
                    f"Hola {cliente.first_name},\n\n"
                    f"Te recordamos que tienes una reserva próxima:\n\n"
                    f"📅 Fecha: {reserva.fecha.strftime('%d/%m/%Y')}\n"
                    f"🕒 Hora: {reserva.hora_inicio.strftime('%H:%M')}\n"
                    f"💇 Corte: {reserva.corte.titulo}\n"
                    f"💈 Barbero: {reserva.barbero.nombre}\n\n"
                    "¡Te esperamos puntual!\n"
                    "Blessed Barbershop"
                )

                send_mail(
                    asunto,
                    mensaje,
                    'blessed.barbershop.oficial10@gmail.com',  # Remitente
                    [cliente.email],          # Destinatario
                    fail_silently=False,
                )
                print(f"✅ Recordatorio enviado a {cliente.email} (Reserva ID: {reserva.id})")

            except Exception as e:
                print(f"❌ Error al enviar recordatorio: {e}")

class RecordatorioReservaCronJob(CronJobBase):
    RUN_EVERY_MINS = 1  # Ejecutar cada minuto para prueba
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'barberiaapp.recordatorio_reserva_cronjob'

    def do(self):
        enviar_recordatorios()
