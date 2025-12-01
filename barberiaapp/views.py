from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Cliente
from .models import Corte, Reserva, Barbero, Admin
from .forms import ReservaForm
from datetime import datetime, timedelta, time
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.contrib.auth import authenticate, login
from datetime import datetime, date
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.contrib import messages
from django.shortcuts import redirect, render
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import re
from django.contrib.auth.hashers import make_password
from django.conf import settings
from django.core.mail import EmailMessage
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.utils import timezone
from io import BytesIO
from datetime import datetime
from django.core.mail import EmailMessage
from django.shortcuts import redirect
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.graphics.barcode import code128
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from .models import Corte, Barbero, Cliente, Reserva
from django.contrib.auth.hashers import check_password



def index(request):
    barberos = Barbero.objects.all()
    return render(request, 'barberiaapp/index.html', {'barberos': barberos})

def reservas(request):
    if not request.session.get('cliente_id'):
        return redirect('login')

    if request.method == 'POST':
        corte_id = request.POST.get('corte')
        barbero_id = request.POST.get('barbero')
        fecha_str = request.POST.get('fecha')
        hora_inicio_str = request.POST.get('hora_inicio')

        if not (corte_id and barbero_id and fecha_str and hora_inicio_str):
            messages.error(request, "Faltan datos en la reserva.")
            return redirect('reservas')

        try:
            corte = Corte.objects.get(pk=corte_id)
            barbero = Barbero.objects.get(pk=barbero_id)
            if not barbero.disponible:
                messages.error(request, "El barbero seleccionado no está disponible.")
                return redirect('reservas')
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            hora_inicio = datetime.strptime(hora_inicio_str, "%H:%M").time()
        except Exception as e:
            messages.error(request, f"Error al procesar la reserva: {e}")
            return redirect('reservas')

        ahora = timezone.localtime()
        hoy = ahora.date()

        if fecha < hoy or (fecha == hoy and hora_inicio <= ahora.time()):
            messages.error(request, "No puedes seleccionar una fecha u hora pasada.")
            return redirect('reservas')

        horas_libres = horarios_disponibles(fecha, corte.duracion, barbero.id)
        if hora_inicio not in horas_libres:
            messages.error(request, "Hora no disponible.")
            return redirect('reservas')

        cliente_id = request.session.get('cliente_id')
        cliente = Cliente.objects.get(pk=cliente_id)
        nombre_cliente = f"{cliente.first_name} {cliente.last_name}"

        # Evita reservas duplicadas en el mismo día
        if Reserva.objects.filter(nombre_cliente=nombre_cliente, fecha=fecha).exists():
            messages.error(request, "Ya tienes una reserva para este día.")
            return redirect('reservas')

        reserva = Reserva.objects.create(
            nombre_cliente=nombre_cliente,
            barbero=barbero,
            corte=corte,
            fecha=fecha,
            hora_inicio=hora_inicio
        )

        # --- Crear boleta electrónica ---
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Encabezado
        pdf.setFont("Helvetica-Bold", 22)
        pdf.drawCentredString(width / 2, height - 70, "Blessed Barbershop")

        # Subtítulo
        pdf.setFont("Helvetica", 12)
        pdf.drawCentredString(width / 2, height - 90, "Estilo, confianza y precisión")

        # Línea separadora
        pdf.setStrokeColor(colors.black)
        pdf.line(50, height - 100, width - 50, height - 100)

        # Datos de empresa
        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, height - 120, "Dirección: Av. Central #123, Santiago, Chile")
        pdf.drawString(50, height - 135, "Correo: blessed.barbershop.oficial10@gmail.com")
        pdf.drawString(50, height - 150, "Teléfono: +56 9 1234 5678")
        pdf.drawString(50, height - 165, "RUT: 77.123.456-7")

        # Línea separadora
        pdf.line(50, height - 180, width - 50, height - 180)

        # Datos de la reserva
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, height - 210, "Boleta Electrónica")

        pdf.setFont("Helvetica", 12)
        pdf.drawString(50, height - 240, f"Cliente: {nombre_cliente}")
        pdf.drawString(50, height - 260, f"Barbero: {barbero.nombre}")
        pdf.drawString(50, height - 280, f"Servicio: {corte.titulo}")
        pdf.drawString(50, height - 300, f"Fecha: {reserva.fecha.strftime('%d/%m/%Y')}")
        pdf.drawString(50, height - 320, f"Hora: {reserva.hora_inicio.strftime('%H:%M')}")
        pdf.drawString(50, height - 340, f"Precio: ${corte.precio:.0f}")

        # Línea separadora
        pdf.line(50, height - 350, width - 50, height - 350)

        # Mensaje final
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(50, height - 380, "Gracias por confiar en Blessed Barbershop.")
        pdf.drawString(50, height - 395, "Recuerde llegar 10 minutos antes de su cita.")
        pdf.drawString(50, height - 410, "Síguenos en Instagram: @blessedbarbershop.cl")

        # Código QR
        qr_code = qr.QrCodeWidget(f"Reserva #{reserva.id} - {nombre_cliente} - {corte.titulo}")
        bounds = qr_code.getBounds()
        size = 70
        w = bounds[2] - bounds[0]
        h = bounds[3] - bounds[1]
        d = Drawing(size, size)
        d.add(qr_code)
        renderPDF.draw(d, pdf, width - 130, height - 330)


        # Pie de página
        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(colors.grey)
        pdf.drawCentredString(width / 2, 40, "Documento generado automáticamente - Blessed Barbershop © 2025")

        pdf.save()
        buffer.seek(0)

        # --- Envío de correo con PDF ---
        try:
            asunto = "Boleta Electrónica - Blessed Barbershop"
            mensaje = (
                f"Hola {cliente.first_name},\n\n"
                f"Adjuntamos tu boleta electrónica correspondiente a tu reserva:\n\n"
                f"📅 Fecha: {reserva.fecha.strftime('%d/%m/%Y')}\n"
                f"🕒 Hora: {reserva.hora_inicio.strftime('%H:%M')}\n"
                f"💇 Corte: {corte.titulo}\n"
                f"💈 Barbero: {barbero.nombre}\n\n"
                "Gracias por preferir Blessed Barbershop.\n"
            )

            email = EmailMessage(
                asunto,
                mensaje,
                'rexmarket26@gmail.com',
                [cliente.email]
            )
            email.attach('boleta_blessedbarbershop.pdf', buffer.getvalue(), 'application/pdf')
            email.send()

            messages.success(request, "Reserva creada y boleta enviada al correo.")
        except Exception as e:
            messages.warning(request, f"Reserva creada, pero hubo un error al enviar el correo: {e}")

        return redirect('reservas')
    # Vista GET
    categoria_actual = request.GET.get('categoria', 'todos')
    cortes = Corte.objects.all() if categoria_actual == 'todos' else Corte.objects.filter(categoria=categoria_actual)
    categorias = dict(Corte.CATEGORIAS).items()
    titulo_categoria = dict(Corte.CATEGORIAS).get(categoria_actual, 'Todos')

    barberos = Barbero.objects.all()

    return render(request, 'barberiaapp/reservas.html', {
        'cortes': cortes,
        'categorias': categorias,
        'categoria_actual': categoria_actual,
        'titulo_categoria': titulo_categoria,
        'barberos': barberos
    })


def login_cliente(request):
    if request.method == 'POST':
        rut = request.POST.get('username')
        password = request.POST.get('password')

        try:
            cliente = Cliente.objects.get(rut=rut)
            if not cliente.activo:
                messages.error(request, "Tu cuenta ha sido bloqueada por el administrador.")
                return redirect('login')

            if check_password(password, cliente.password):
                request.session['cliente_id'] = cliente.id
                request.session['cliente_nombre'] = cliente.first_name
                request.session['cliente_apellido'] = cliente.last_name
                request.session['tipo_usuario'] = 'cliente'
                return redirect('index')
            else:
                messages.error(request, "Contraseña incorrecta.")
                return redirect('login')

        except Cliente.DoesNotExist:
            pass  

        try:
            barbero = Barbero.objects.get(rut=rut)
            if check_password(password, barbero.contraseña):
                request.session['barbero_id'] = barbero.id
                request.session['barbero_nombre'] = barbero.nombre
                request.session['tipo_usuario'] = 'barbero'
                return redirect('ver_reservas')
            else:
                messages.error(request, "Contraseña incorrecta.")
                return redirect('login')

        except Barbero.DoesNotExist:
            pass

        try:
            admin = Admin.objects.get(rut=rut)
            if check_password(password, admin.contraseña):
                request.session['admin_id'] = admin.id
                request.session['tipo_usuario'] = 'admin'
                return redirect('panel_servicios')
            else:
                messages.error(request, "Contraseña incorrecta.")
                return redirect('login')

        except Admin.DoesNotExist:
            pass

        messages.error(request, "RUT o contraseña incorrecta.")
        return redirect('login')

    return render(request, 'barberiaapp/registro/login.html')

from barberiaapp.utils import validar_rut


def registrar_cliente(request):
    if request.method == 'POST':
        rut = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password1')
        password2 = request.POST.get('password2')

        first_name = first_name.strip().title()
        last_name = last_name.strip().title()

        data = {
            'username': rut,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
        }

        # Validaciones
        if not all([rut, first_name, last_name, email, password, password2]):
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, 'barberiaapp/registro/signup.html', data)

        if password != password2:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, 'barberiaapp/registro/signup.html', data)
        
        # Validación nombre
        if len(first_name) < 2 or not re.match(r"^[A-Za-zÁÉÍÓÚÑáéíóúñ\s]+$", first_name):
            messages.error(request, "El nombre no es válido. Solo debe contener letras.")
            return render(request, 'barberiaapp/registro/signup.html', data)

        if len(last_name) < 2 or not re.match(r"^[A-Za-zÁÉÍÓÚÑáéíóúñ\s]+$", last_name):
            messages.error(request, "El apellido no es válido. Solo debe contener letras.")
            return render(request, 'barberiaapp/registro/signup.html', data)

        if first_name.isspace() or last_name.isspace():
            messages.error(request, "El nombre y apellido no pueden estar vacíos.")
            return render(request, 'barberiaapp/registro/signup.html', data)
        
        password_regex = r'^(?=.*[A-Z])(?=.*\d).{8,}$'

        if not re.match(password_regex, password):
            messages.error(request, "La contraseña debe tener mínimo 8 caracteres, incluir al menos una mayúscula y un número.")
            return render(request, 'barberiaapp/registro/signup.html', data)
        
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "El correo electrónico no es válido.")
            return render(request, 'barberiaapp/registro/signup.html', data)

        if not validar_rut(rut):
            messages.error(request, "El RUT ingresado no es válido.")
            return render(request, 'barberiaapp/registro/signup.html', data)

        if Cliente.objects.filter(rut=rut).exists():
            messages.error(request, "Este RUT ya está registrado.")
            return render(request, 'barberiaapp/registro/signup.html', data)

        if Cliente.objects.filter(email=email).exists():
            messages.error(request, "Este correo electrónico ya está registrado.")
            return render(request, 'barberiaapp/registro/signup.html', data)

        cliente = Cliente(
            rut=rut,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=make_password(password)
        )
        cliente.save()

        messages.success(request, "Registro exitoso. Ya puedes iniciar sesión.")
        return redirect('login')

    return render(request, 'barberiaapp/registro/signup.html')

def logout_cliente(request):
    request.session.flush()  
    return redirect('index')

def generar_horarios(duracion):
    inicio = time(9, 0)
    fin = time(20, 0)
    horarios = []

    actual = datetime.combine(datetime.today(), inicio)

    while actual.time() <= (datetime.combine(datetime.today(), fin) - timedelta(minutes=duracion)).time():
        horarios.append(actual.time())
        actual += timedelta(minutes=30)

    return horarios


def horarios_disponibles(fecha, duracion, barbero_id):
    posibles = generar_horarios(duracion)
    reservas = Reserva.objects.filter(fecha=fecha, barbero_id=barbero_id).exclude(estado='cancelada')

    ocupados = []
    for reserva in reservas:
        start = datetime.combine(fecha, reserva.hora_inicio)
        end = datetime.combine(fecha, reserva.hora_fin)
        while start < end:
            ocupados.append(start.time())
            start += timedelta(minutes=30)

    ahora = timezone.localtime()
    limite = (ahora + timedelta(hours=1)).time()

    if fecha == ahora.date():
        posibles = [hora for hora in posibles if hora > limite]

    disponibles = [hora for hora in posibles if hora not in ocupados]
    return disponibles




def api_horas_disponibles(request):
    corte_id = request.GET.get('corte')
    fecha_str = request.GET.get('fecha')
    barbero_id = request.GET.get('barbero') 

    if not (corte_id and fecha_str and barbero_id):
        return JsonResponse([], safe=False)

    try:
        corte = Corte.objects.get(pk=corte_id)
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        horas = horarios_disponibles(fecha, corte.duracion, barbero_id)
        horas_str = [hora.strftime("%H:%M") for hora in horas]
        return JsonResponse(horas_str, safe=False)
    except Exception:
        return JsonResponse([], safe=False)



from django.utils import timezone
from datetime import datetime, timedelta, date

def mis_reservas(request):
    if not request.session.get('cliente_id'):
        return redirect('login')

    cliente_id = request.session.get('cliente_id')
    cliente = Cliente.objects.get(pk=cliente_id)
    nombre_cliente = f"{cliente.first_name} {cliente.last_name}"

    if request.method == 'POST':
        accion = request.POST.get('accion')
        reserva_id = request.POST.get('reserva_id')

        try:
            reserva = Reserva.objects.get(id=reserva_id, nombre_cliente=nombre_cliente)
        except Reserva.DoesNotExist:
            messages.error(request, "Reserva no encontrada.")
            return redirect('mis_reservas')

        ahora = timezone.now()
        inicio_reserva = timezone.make_aware(datetime.combine(reserva.fecha, reserva.hora_inicio))
        diferencia = inicio_reserva - ahora

        # Cancelar reserva
        if accion == 'cancelar':
            if diferencia <= timedelta(hours=2):
                messages.error(request, "No puedes cancelar una reserva con menos de 2 horas de anticipación.")
            else:
                reserva.estado = 'cancelada'
                reserva.save()

        # Enviar correo de confirmación de cancelación
            asunto = "Confirmación de cancelación - Blessed Barbershop"
            mensaje = f"""
            Hola {cliente.first_name},

        Tu reserva ha sido cancelada exitosamente.

Detalles de la reserva cancelada:
- Fecha original: {reserva.fecha.strftime('%d/%m/%Y')}
- Hora: {reserva.hora_inicio.strftime('%H:%M')}
- Servicio: {reserva.corte.titulo}
- Barbero: {reserva.barbero.nombre}

Lamentamos no verte esta vez, pero esperamos atenderte pronto 💈
Gracias por preferir Blessed Barbershop.
"""

            destinatario = [cliente.email]
            try:
                send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, destinatario)
            except Exception as e:
                print("Error al enviar correo de cancelación:", e)

            messages.success(request, "Reserva cancelada exitosamente y correo enviado.")
            return redirect('mis_reservas')

        # Editar reserva
        elif accion == 'editar':
            if reserva.editado:
                messages.error(request, "Esta reserva ya fue editada una vez. No se puede volver a editar.")
                return redirect('mis_reservas')

            if diferencia <= timedelta(hours=2):
                messages.error(request, "No puedes editar una reserva con menos de 2 horas de anticipación.")
                return redirect('mis_reservas')

            nueva_fecha = request.POST.get('nueva_fecha')
            nueva_hora = request.POST.get('nueva_hora')

            if not nueva_fecha or not nueva_hora:
                messages.error(request, "Debes ingresar fecha y hora válidas.")
                return redirect('mis_reservas')

            try:
                nueva_fecha_dt = datetime.strptime(nueva_fecha, "%Y-%m-%d").date()
                nueva_hora_dt = datetime.strptime(nueva_hora, "%H:%M").time()
            except ValueError:
                messages.error(request, "Formato de fecha u hora incorrecto.")
                return redirect('mis_reservas')

            if nueva_fecha_dt < date.today():
                messages.error(request, "La fecha no puede ser anterior a hoy.")
                return redirect('mis_reservas')

            # Validar disponibilidad
            horas_libres = horarios_disponibles(nueva_fecha_dt, reserva.corte.duracion, reserva.barbero.id)
            if nueva_hora_dt not in horas_libres:
                messages.error(request, "La hora seleccionada ya está ocupada.")
                return redirect('mis_reservas')

            # Actualizar reserva
            reserva.fecha = nueva_fecha_dt
            reserva.hora_inicio = nueva_hora_dt
            reserva.editado = True
            reserva.save()

            # Enviar correo de confirmación
            asunto = "Confirmación de cambio de reserva - Blessed Barbershop"
            mensaje = f"""
Hola {cliente.first_name},

Tu reserva ha sido modificada exitosamente.

Detalles actualizados:
- Fecha: {reserva.fecha.strftime('%d/%m/%Y')}
- Hora: {reserva.hora_inicio.strftime('%H:%M')}
- Servicio: {reserva.corte.titulo}
- Barbero: {reserva.barbero.nombre}

Gracias por preferir Blessed Barbershop.
Nos vemos pronto 💈
"""
            destinatario = [cliente.email]
            try:
                send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, destinatario)
            except Exception as e:
                print("Error al enviar correo:", e)

            messages.success(request, "Reserva actualizada exitosamente y correo enviado.")
            return redirect('mis_reservas')

    # Mostrar reservas
    reservas = Reserva.objects.filter(nombre_cliente=nombre_cliente).order_by('-fecha', '-hora_inicio')

    ahora = timezone.now()
    for reserva in reservas:
        inicio_reserva = timezone.make_aware(datetime.combine(reserva.fecha, reserva.hora_inicio))
        reserva.puede_cancelar = (inicio_reserva - ahora) > timedelta(hours=2)
        reserva.puede_editar = not reserva.editado and (inicio_reserva - ahora) > timedelta(hours=2)

    # Mostrar reservas
    reservas = Reserva.objects.filter(nombre_cliente=nombre_cliente)

# 🔹 Aplicar filtros según lo que el usuario elija
    filtro = request.GET.get('filtro')

    if filtro == 'recientes':   
        reservas = reservas.order_by('-fecha', '-hora_inicio')
    elif filtro == 'antiguas':
        reservas = reservas.order_by('fecha', 'hora_inicio')
    elif filtro == 'pendientes':
        reservas = reservas.filter(estado='pendiente').order_by('-fecha', '-hora_inicio')
    elif filtro == 'canceladas':
        reservas = reservas.filter(estado='cancelada').order_by('-fecha', '-hora_inicio')
    elif filtro == 'realizadas':
        reservas = reservas.filter(estado='realizada').order_by('-fecha', '-hora_inicio')
    else:
        reservas = reservas.order_by('-fecha', '-hora_inicio')  # por defecto

# Calcular permisos de edición/cancelación
    ahora = timezone.now()
    for reserva in reservas:
        inicio_reserva = timezone.make_aware(datetime.combine(reserva.fecha, reserva.hora_inicio))
        reserva.puede_cancelar = (inicio_reserva - ahora) > timedelta(hours=2)
        reserva.puede_editar = not reserva.editado and (inicio_reserva - ahora) > timedelta(hours=2)


    return render(request, 'barberiaapp/mis_reservas.html', {
    'reservas': reservas,
    'cliente': cliente,
    'today': date.today(),
    'filtro_actual': filtro or 'recientes'
})


@require_http_methods(["GET", "POST"])
def ver_reservas_barbero(request):
    barbero_id = request.session.get('barbero_id')
    if not barbero_id:
        return redirect('login_barbero')

    barbero = Barbero.objects.get(pk=barbero_id)
    reservas = Reserva.objects.filter(barbero=barbero).order_by('fecha', 'hora_inicio')

    if request.method == 'POST':
        reserva_id = request.POST.get('reserva_id')
        accion = request.POST.get('accion')

        try:
            reserva = Reserva.objects.get(id=reserva_id, barbero=barbero)
            if accion == 'cambiar_estado':
                nuevo_estado = request.POST.get('estado')
                if nuevo_estado in dict(Reserva.ESTADOS_RESERVA).keys():
                    reserva.estado = nuevo_estado
                    reserva.save()
                    messages.success(request, f"Estado actualizado a '{reserva.get_estado_display()}'.")
                else:
                    messages.error(request, "Estado no válido.")
            else:
                messages.error(request, "Acción no válida.")

        except Reserva.DoesNotExist:
            messages.error(request, "No se encontró la reserva.")

        return redirect('ver_reservas')

    # Filtros GET
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    estado = request.GET.get('estado')

    if fecha_inicio:
        reservas = reservas.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        reservas = reservas.filter(fecha__lte=fecha_fin)
    if estado:
        reservas = reservas.filter(estado=estado)

    # Manejo de acciones POST (cambiar estado / eliminar)
    if request.method == "POST":
        reserva_id = request.POST.get("reserva_id")
        accion = request.POST.get("accion")
        if accion == "cambiar_estado":
            nuevo_estado = request.POST.get("estado")
            Reserva.objects.filter(id=reserva_id).update(estado=nuevo_estado)
        return redirect("panel_barbero_reservas")

    return render(request, 'barberiaapp/ver_reservas.html', {
        'barbero': barbero,
        'reservas': reservas
    })



#aqui manuel

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now
from .models import Reserva, Cliente  # ajusta según tu modelo

@csrf_exempt
def chatbox_interactivo(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body)
        pregunta = data.get('pregunta', '').strip()
        cliente_id = request.session.get('cliente_id')

        if not cliente_id:
            return JsonResponse({"respuesta": "Debes iniciar sesión para usar el chat."})

        cliente = Cliente.objects.get(pk=cliente_id)
        nombre_cliente = f"{cliente.first_name} {cliente.last_name}"

        # Opción: Ver mis reservas
        if "mis reservas" in pregunta.lower():
            reservas = Reserva.objects.filter(nombre_cliente=nombre_cliente).order_by('fecha', 'hora_inicio')
            if reservas.exists():
                respuesta = "Estas son tus reservas:\n"
                for r in reservas:
                    respuesta += f"🗓 {r.fecha} - {r.hora_inicio.strftime('%H:%M')} con {r.barbero.nombre}\n"
            else:
                respuesta = "No tienes reservas registradas."
            return JsonResponse({"respuesta": respuesta})

        # Opción: Solicitar lista de barberos para disponibilidad
        elif "disponibilidad" in pregunta.lower() and "barbero" not in pregunta.lower():
            # Enviar la lista de barberos para mostrar botones en frontend
            barberos = list(Barbero.objects.all().values('id', 'nombre'))
            return JsonResponse({"barberos": barberos})

        # Opción: Consultar disponibilidad de un barbero específico
        elif pregunta.lower().startswith("disponibilidad barbero"):
            # Formato esperado: "disponibilidad barbero <id>"
            partes = pregunta.split()
            if len(partes) == 3 and partes[2].isdigit():
                barbero_id = int(partes[2])
                try:
                    barbero = Barbero.objects.get(pk=barbero_id)
                    # Por simplicidad, seleccionamos un corte estándar o el primero que tenga ese barbero (ajusta si tienes lógica distinta)
                    corte = Corte.objects.first()
                    if not corte:
                        return JsonResponse({"respuesta": "No se encontró información del corte."})

                    fecha = date.today()
                    horas = horarios_disponibles(fecha, corte.duracion, barbero_id)
                    if horas:
                        horas_str = [hora.strftime("%H:%M") for hora in horas]
                        respuesta = f"Horas disponibles hoy con {barbero.nombre}:\n" + "\n".join(f"🕒 {h}" for h in horas_str)
                    else:
                        respuesta = f"No hay horas disponibles para hoy con {barbero.nombre}."
                    return JsonResponse({"respuesta": respuesta})

                except Barbero.DoesNotExist:
                    return JsonResponse({"respuesta": "Barbero no encontrado."})

            else:
                return JsonResponse({"respuesta": "Formato de pregunta incorrecto para disponibilidad de barbero."})

        # Pregunta no reconocida
        else:
            return JsonResponse({"respuesta": "Lo siento, no entendí la pregunta. Puedes elegir una opción arriba."})

    except Exception as e:
        return JsonResponse({"respuesta": f"Error: {str(e)}"})

from django.http import JsonResponse
from .models import Barbero

def api_barberos(request):
    barberos = Barbero.objects.all().values('id', 'nombre')
    return JsonResponse(list(barberos), safe=False)



import random
import string


def solicitar_recuperacion(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            cliente = Cliente.objects.get(email=email)
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

            request.session['codigo_recuperacion'] = code
            request.session['cliente_email'] = email

            send_mail(
                'Código de recuperación - Blessed Barbershop',
                f'Tu código de recuperación es: {code}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            return redirect('verificar_codigo')

        except Cliente.DoesNotExist:
            return render(request, 'barberiaapp/registro/recuperacion_contra/recuperar_contraseña.html', {
                'error': 'No existe una cuenta con ese correo.'
            })
    return render(request, 'barberiaapp/registro/recuperacion_contra/recuperar_contraseña.html')

def verificar_codigo(request):
    if request.method == 'POST':
        codigo_ingresado = request.POST.get('codigo')
        codigo_real = request.session.get('codigo_recuperacion')

        if codigo_ingresado == codigo_real:
            return redirect('cambiar_contraseña')
        else:
            return render(request, 'barberiaapp/registro/recuperacion_contra/verificar_codigo.html', {
                'error': 'Código incorrecto. Intenta nuevamente.'
            })
    return render(request, 'barberiaapp/registro/recuperacion_contra/verificar_codigo.html')


def cambiar_contraseña(request):
    if request.method == 'POST':
        nueva = request.POST.get('nueva')
        confirmar = request.POST.get('confirmar')
        email = request.session.get('cliente_email')

        if nueva != confirmar:
            return render(request, 'barberiaapp/registro/recuperacion_contra/cambiar_contraseña.html', {
                'error': 'Las contraseñas no coinciden.'
            })

        try:
            cliente = Cliente.objects.get(email=email)
            cliente.password = make_password(nueva)
            cliente.save()

            request.session.pop('codigo_recuperacion', None)
            request.session.pop('cliente_email', None)

            messages.success(request, 'Contraseña cambiada exitosamente. Ya puedes iniciar sesión.')
            return redirect('login')
        except Cliente.DoesNotExist:
            messages.error(request, 'Error al cambiar la contraseña.')
            return redirect('solicitar_recuperacion')
    return render(request, 'barberiaapp/registro/recuperacion_contra/cambiar_contraseña.html')



from django.db.models import Count

def panel_barbero(request):
    if not request.session.get('barbero_id'):
        return redirect('login_barbero')

    barbero_id = request.session.get('barbero_id')
    barbero = Barbero.objects.get(pk=barbero_id)

    # Filtros por fecha
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    categoria = request.GET.get('categoria')  # opcional: filtrar por tipo de servicio

    reservas = Reserva.objects.filter(barbero=barbero, estado='realizada')

    if fecha_inicio:
        reservas = reservas.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        reservas = reservas.filter(fecha__lte=fecha_fin)
    if categoria and categoria != "todas":
        reservas = reservas.filter(corte__categoria=categoria)

    # Resumen
    clientes_atendidos_totales = reservas.count()
    clientes_atendidos_unicos = reservas.values('nombre_cliente').distinct().count()

    # Estadísticas por mes
    reservas_por_mes_qs = reservas.values('fecha__month').annotate(total=Count('id')).order_by('fecha__month')
    meses = [r['fecha__month'] for r in reservas_por_mes_qs]
    totales_por_mes = [r['total'] for r in reservas_por_mes_qs]
    total_reservas = sum(totales_por_mes)

    # Estadísticas por categoría
    reservas_por_categoria_qs = reservas.values('corte__categoria').annotate(total=Count('id'))
    categorias = [r['corte__categoria'] for r in reservas_por_categoria_qs]
    totales_por_categoria = [r['total'] for r in reservas_por_categoria_qs]

    return render(request, 'barberiaapp/panel_barbero.html', {
        'barbero': barbero,
        'clientes_atendidos_totales': clientes_atendidos_totales,
        'clientes_atendidos_unicos': clientes_atendidos_unicos,
        'meses': meses,
        'totales_por_mes': totales_por_mes,
        'total_reservas': total_reservas,
        'categorias': categorias,
        'totales_por_categoria': totales_por_categoria,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'categoria_filtrada': categoria or "todas",
    })


from django.contrib.auth.decorators import user_passes_test


from functools import wraps
from django.shortcuts import redirect

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('admin_id'):
            return redirect('login') 
        return view_func(request, *args, **kwargs)
    return wrapper

from django.db.models import Count
from django.db.models.functions import ExtractWeek, ExtractYear
from .models import Reserva, Corte, Barbero

def panel_servicios(request):
    cortes = Corte.objects.all()
    barberos = Barbero.objects.all()
    clientes = Cliente.objects.all()

    reservas_por_semana = (
        Reserva.objects
        .annotate(
            semana=ExtractWeek('fecha'),
            anio=ExtractYear('fecha')
        )
        .values('anio', 'semana')
        .annotate(total=Count('id'))
        .order_by('anio', 'semana')
    )

    # 💈 Reservas por barbero
    reservas_por_barbero = (
        Reserva.objects
        .values('barbero__nombre')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    # 💇 Cortes más solicitados
    reservas_por_corte = (
        Reserva.objects
        .values('corte__titulo')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    return render(request, 'barberiaapp/admin_panel/panel_servicios.html', {
        'cortes': cortes,
        'barberos': barberos,
        'reservas_por_semana': list(reservas_por_semana),
        'reservas_por_barbero': list(reservas_por_barbero),
        'reservas_por_corte': list(reservas_por_corte),
        'clientes': clientes,
    })
@admin_required
def crear_corte(request):
    if request.method == 'POST':
        Corte.objects.create(
            categoria=request.POST['categoria'],
            titulo=request.POST['titulo'],
            duracion=request.POST['duracion'],
            precio=request.POST['precio'],
            descripcion=request.POST['descripcion'],
        )
        return redirect('panel_servicios')
    return render(request, 'barberiaapp/admin_panel/crear_corte.html')

@admin_required
def editar_corte(request, id):
    corte = get_object_or_404(Corte, id=id)
    if request.method == 'POST':
        corte.categoria = request.POST['categoria']
        corte.titulo = request.POST['titulo']
        corte.duracion = request.POST['duracion']
        corte.precio = request.POST['precio']
        corte.descripcion = request.POST['descripcion']
        corte.save()
        return redirect('panel_servicios')
    return render(request, 'barberiaapp/admin_panel/editar_corte.html', {'corte': corte})

@admin_required
def eliminar_corte(request, id):
    corte = get_object_or_404(Corte, id=id)
    corte.delete()
    return redirect('panel_servicios')

@admin_required
def crear_barbero(request):
    if request.method == 'POST':
        Barbero.objects.create(
            nombre=request.POST['nombre'],
            descripcion=request.POST['descripcion'],
            cortes_destacados=request.POST['cortes_destacados'],
            especialidad=request.POST['especialidad'],
            rut=request.POST['rut'],
            contraseña=make_password(request.POST['contraseña']), 
        )
        return redirect('panel_servicios')
    return render(request, 'barberiaapp/admin_panel/crear_barbero.html')


@admin_required
def editar_barbero(request, id):
    barbero = get_object_or_404(Barbero, id=id)
    if request.method == 'POST':
        barbero.nombre = request.POST['nombre']
        barbero.descripcion = request.POST['descripcion']
        barbero.cortes_destacados = request.POST['cortes_destacados']
        barbero.especialidad = request.POST['especialidad']
        barbero.rut = request.POST['rut']

        nueva_contraseña = request.POST['contraseña']

        if nueva_contraseña and not nueva_contraseña.startswith('pbkdf2_'):
            barbero.contraseña = make_password(nueva_contraseña)

        barbero.save()
        return redirect('panel_servicios')

    return render(request, 'barberiaapp/admin_panel/editar_barbero.html', {'barbero': barbero})

@admin_required
def eliminar_barbero(request, id):
    barbero = get_object_or_404(Barbero, id=id)
    barbero.delete()
    return redirect('panel_servicios')

@admin_required
def cambiar_disponibilidad_barbero(request, id):
    barbero = get_object_or_404(Barbero, id=id)
    barbero.disponible = not barbero.disponible
    barbero.save()
    return redirect('panel_servicios')

@admin_required
def bloquear_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    cliente.activo = False
    cliente.save()
    messages.success(request, f"El cliente {cliente.first_name} ha sido bloqueado.")
    return redirect('panel_servicios')

@admin_required
def desbloquear_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    cliente.activo = True
    cliente.save()
    messages.success(request, f"El cliente {cliente.first_name} ha sido desbloqueado.")
    return redirect('panel_servicios')