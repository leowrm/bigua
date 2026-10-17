from django.core.management.base import BaseCommand

from whatsapp.scheduler import CobrancaScheduler


class Command(BaseCommand):
    """
    Verifica as mensalidades pendentes e cria registros de DisparoWhatsApp
    (status AGENDADO) para quem está em pré-vencimento, vencimento ou atraso,
    de acordo com a ConfiguracaoWhatsApp ativa.

    Não envia nada pelo WhatsApp — só agenda. Quem envia de fato é o
    comando `enviar_disparos_whatsapp`.

    Uso manual:
        python manage.py gerar_disparos_whatsapp

    Agendado via django-crontab (ver CRONJOBS em settings.py).
    """

    help = (
        "Gera os disparos de cobrança (pré-vencimento/vencimento/atraso) "
        "com base nas mensalidades pendentes."
    )

    def handle(self, *args, **options):
        criados_antes = self._contar_agendados()

        CobrancaScheduler().executar()

        criados_depois = self._contar_agendados()
        novos = criados_depois - criados_antes

        self.stdout.write(
            self.style.SUCCESS(
                f"Scheduler executado. {novos} novo(s) disparo(s) agendado(s)."
            )
        )

    @staticmethod
    def _contar_agendados():
        from whatsapp.models import DisparoWhatsApp

        return DisparoWhatsApp.objects.filter(status="AGENDADO").count()
