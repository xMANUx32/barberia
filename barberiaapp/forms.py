from django import forms

from .models import Reserva, Corte
from datetime import datetime, time, timedelta


class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ['nombre_cliente', 'corte', 'fecha', 'hora_inicio']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'hora_inicio': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        self.disponibles = kwargs.pop('horas_disponibles', None)
        super().__init__(*args, **kwargs)

        if self.disponibles is not None:
            self.fields['hora_inicio'].widget.choices = [
                (h.strftime("%H:%M"), h.strftime("%H:%M")) for h in self.disponibles
            ]

