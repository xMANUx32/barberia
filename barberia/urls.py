"""
URL configuration for barberia project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from barberiaapp.views import *
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('reservas/', reservas, name='reservas'),
    path('signup/', registrar_cliente, name='signup'),
    path('login/', login_cliente, name='login'),
    path('logout/', logout_cliente, name='logout'),
    path('api/horas-disponibles/', api_horas_disponibles, name='api_horas_disponibles'),
    path('mis-reservas/', mis_reservas, name='mis_reservas'),
    path('ver-reservas/', ver_reservas_barbero, name='ver_reservas'),
    path('api/chatbox/', chatbox_interactivo, name='chatbox_interactivo'),
    path('api/barberos/', api_barberos, name='api_barberos'),
    path('password_reset/', solicitar_recuperacion, name='solicitar_recuperacion'),
    path('verificar_codigo/', verificar_codigo, name='verificar_codigo'),
    path('cambiar_contraseña/', cambiar_contraseña, name='cambiar_contraseña'),
    path('panel_barbero/', panel_barbero, name='panel_barbero'),
    path('panel_servicios/', panel_servicios, name='panel_servicios'),
    path('crear_corte/', crear_corte, name='crear_corte'),
    path('editar_corte/<int:id>/', editar_corte, name='editar_corte'),
    path('eliminar_corte/<int:id>/', eliminar_corte, name='eliminar_corte'),
    path('crear_barbero/', crear_barbero, name='crear_barbero'),
    path('editar_barbero/<int:id>/', editar_barbero, name='editar_barbero'),
    path('eliminar_barbero/<int:id>/', eliminar_barbero, name='eliminar_barbero'),
    path('barberos/<int:id>/cambiar_disponibilidad/', cambiar_disponibilidad_barbero, name='cambiar_disponibilidad_barbero'),
    path('clientes/<int:id>/bloquear/', bloquear_cliente, name='bloquear_cliente'),
    path('clientes/<int:id>/desbloquear/', desbloquear_cliente, name='desbloquear_cliente'),


]
