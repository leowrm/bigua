from django.core.management.base import BaseCommand

from whatsapp.models import DisparoWhatsApp
from whatsapp.sender import MetaSender


class Command(BaseCommand):
    """
    Envia, via WhatsApp Cloud API, todos os DisparoWhatsApp com status
    AGENDADO, atualizando o status para ENVIADO ou FALHOU conforme o
    resultado.

    Antes deste comando existir, MetaSender.enviar_pendentes() nunca era
    chamado em lugar nenhum do projeto, então os disparos agendados pelo
    scheduler nunca saíam do banco.

    Uso manual:
        python manage.py enviar_disparos_whatsapp

    Agendado via django-crontab (ver CRONJOBS em settings.py).
    """

    help = "Envia pelo WhatsApp os disparos agendados (status AGENDADO)."

    def handle(self, *args, **options):
        pendentes = DisparoWhatsApp.objects.filter(status="AGENDADO").count()

        if pendentes == 0:
            self.stdout.write("Nenhum disparo agendado para enviar.")
            return

        MetaSender().enviar_pendentes()

        enviados = DisparoWhatsApp.objects.filter(status="ENVIADO").count()
        falhas = DisparoWhatsApp.objects.filter(status="FALHOU").count()

        self.stdout.write(
            self.style.SUCCESS(
                f"{pendentes} disparo(s) processado(s). "
                f"Enviados até agora: {enviados}. Falhas até agora: {falhas}."
            )
        )
