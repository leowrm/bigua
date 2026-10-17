from datetime import date

from django.utils import timezone

from v1.models import Mensalidades

from .models import (
    ConfiguracaoWhatsApp,
    DisparoWhatsApp
)


class CobrancaScheduler:

    def executar(self):

        config = ConfiguracaoWhatsApp.objects.filter(
            ativo=True
        ).first()

        if not config:
            return

        hoje = date.today()

        mensalidades = Mensalidades.objects.filter(
            estado_pagamento__iexact="PENDENTE"
        )

        for mensalidade in mensalidades:

            if not mensalidade.data_vencimento:
                continue

            dias = (
                mensalidade.data_vencimento - hoje
            ).days

            if dias == config.dias_aviso_antes:

                self.criar_disparo(
                    mensalidade,
                    config.mensagem_aviso_antes,
                    "PRE_VENCIMENTO"
                )

            elif dias == 0:

                self.criar_disparo(
                    mensalidade,
                    config.mensagem_vencimento,
                    "VENCIMENTO"
                )

            elif dias == -config.dias_aviso_atraso:

                self.criar_disparo(
                    mensalidade,
                    config.mensagem_aviso_atraso,
                    "ATRASO"
                )

    def criar_disparo(
        self,
        mensalidade,
        template,
        tipo
    ):

        associado = mensalidade.id_associado

        ja_existe = DisparoWhatsApp.objects.filter(
            mensalidade=mensalidade,
            tipo=tipo
        ).exists()

        if ja_existe:
            return

        mensagem = (
            template
            .replace(
                "{{nome}}",
                associado.nome
            )
            .replace(
                "{{valor}}",
                str(mensalidade.valor)
            )
            .replace(
                "{{data_vencimento}}",
                mensalidade.data_vencimento.strftime(
                    "%d/%m/%Y"
                )
            )
        )

        DisparoWhatsApp.objects.create(
            associado=associado,
            mensalidade=mensalidade,
            mensagem=mensagem,
            tipo=tipo,
            status="AGENDADO",
            data_programada=timezone.now()
        )