from v1.models import Associado
from v1.models import Mensalidades

from .models import (
    ConversaWhatsApp,
    EstadoConversa,
    ConfiguracaoWhatsApp
)
from .sender import formatar_telefone


class WhatsAppService:

    def menu_principal(self):

        return """
Olá!

Escolha uma opção:

1 - Consultar mensalidades abertas

2 - Fazer doação

3 - Falar com atendente
"""

    def _variacoes_telefone(self, telefone):
        """
        Gera as diferentes formas como esse número pode estar salvo
        no cadastro do associado.

        A Meta manda o número de quem escreveu SEM o 9º dígito
        (ex: 555186434826), mas o cadastro de associados pode ter
        sido preenchido com o número "completo", do jeito que as
        pessoas normalmente digitam (ex: 5551986434826, ou até só
        51986434826, sem o DDI). Por isso comparamos com todas as
        variações possíveis em vez de um único formato fixo.
        """

        sem_nono_digito = formatar_telefone(telefone)

        variacoes = {sem_nono_digito}

        # Com o 9º dígito de volta (DDI + DDD + 9 + resto)
        variacoes.add(
            sem_nono_digito[:4] + "9" + sem_nono_digito[4:]
        )

        # Sem o DDI (55), do jeito que alguns cadastros antigos guardam
        variacoes.update({v[2:] for v in list(variacoes)})

        return variacoes

    def buscar_associado_por_telefone(
        self,
        telefone
    ):

        variacoes = self._variacoes_telefone(telefone)

        return Associado.objects.filter(
            telefone__in=variacoes
        ).first()

    def salvar_mensagem(
        self,
        telefone,
        mensagem,
        direcao,
        associado=None
    ):

        ConversaWhatsApp.objects.create(
            associado=associado,
            telefone=telefone,
            mensagem=mensagem,
            direcao=direcao
        )

    def obter_estado(
        self,
        telefone
    ):

        estado = EstadoConversa.objects.filter(
            telefone=telefone
        ).first()

        if not estado:

            estado = EstadoConversa.objects.create(
                telefone=telefone,
                estado="MENU"
            )

        return estado

    def alterar_estado(
        self,
        telefone,
        novo_estado
    ):

        estado = self.obter_estado(
            telefone
        )

        estado.estado = novo_estado
        estado.save()

    def consultar_mensalidades_abertas(self, telefone):

        associado = self.buscar_associado_por_telefone(
            telefone
        )

        if not associado:
            return "Não encontramos seu cadastro com este número."

        mensalidades = (
            Mensalidades.objects
            .filter(
                id_associado=associado,
                estado_pagamento__in=["Pendente", "Atrasado"],
            )
            .order_by("vencimento", "periodo_referencia")
        )

        if not mensalidades.exists():

            return (
                f"{associado.nome} "
                f"não possui mensalidades abertas."
            )

        linhas = [f"{associado.nome}, estas são suas mensalidades abertas:"]
        for mensalidade in mensalidades:
            linhas.append(
                "\n".join([
                    f"\n• Vencimento: {mensalidade.vencimento.strftime('%d/%m/%Y')}",
                    f"  Valor: R$ {mensalidade.valor}",
                    f"  Status: {mensalidade.estado_pagamento}",
                ])
            )
        return "\n".join(linhas)

    consultar_situacao = consultar_mensalidades_abertas

    def processar_mensagem(
        self,
        texto,
        telefone
    ):

        texto = texto.strip()

        estado = self.obter_estado(
            telefone
        )

        if texto == "1":
            self.alterar_estado(telefone, "CONSULTA_MENSALIDADES")
            return self.consultar_mensalidades_abertas(telefone)

        elif texto == "2":

            self.alterar_estado(telefone, "DOACAO")

            config = ConfiguracaoWhatsApp.objects.filter(ativo=True).first()
            chave_pix = config.chave_pix.strip() if config and config.chave_pix else ""
            if not chave_pix:
                return "No momento, a chave Pix para doações ainda não foi configurada."
            return f"Para fazer uma doação, utilize esta chave Pix:\n\n{chave_pix}"

        elif texto == "3":

            self.alterar_estado(
                telefone,
                "HUMANO"
            )

            config = ConfiguracaoWhatsApp.objects.filter(
                ativo=True
            ).first()

            numero_humano = (
                config.numero_atendimento_humano
                if config and config.numero_atendimento_humano
                else None
            )

            if numero_humano:
                link = f"https://wa.me/{formatar_telefone(numero_humano)}"
                return f"""
Você será atendido pela nossa equipe.

Clique aqui para continuar por lá: {link}
"""

            return "Você será atendido pela nossa equipe em breve."

        return self.menu_principal()
