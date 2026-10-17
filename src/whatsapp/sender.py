import logging
import os

import requests
from django.utils import timezone

from .models import DisparoWhatsApp

logger = logging.getLogger(__name__)

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_VERSION = os.environ.get("WHATSAPP_API_VERSION", "v23.0")

GRAPH_URL = (
    f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/"
    f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
)


def formatar_telefone(telefone):
    """
    Formata o telefone para o padrão que a WhatsApp Cloud API espera
    para números brasileiros.

    IMPORTANTE: para celulares do Brasil, a API do WhatsApp identifica
    a conta pelo formato ANTIGO, sem o 9º dígito extra (DDI + DDD + 8
    dígitos), mesmo que o número "oficial" hoje tenha 9 dígitos depois
    do DDD. Mandar com o 9 faz a Meta responder "accepted" só que pra
    um wa_id diferente do celular de verdade - a mensagem nunca chega.
    Por isso removemos esse 9 extra aqui antes de enviar.
    """

    numero = "".join(
        char for char in telefone if char.isdigit()
    )

    if not numero.startswith("55"):
        numero = f"55{numero}"

    # 55 + DDD (2 dígitos) + 9 + 8 dígitos = 13 dígitos ao todo.
    # Se o 5º dígito (logo após DDI + DDD) for "9", removemos.
    if len(numero) == 13 and numero[4] == "9":
        numero = numero[:4] + numero[5:]

    return numero


def enviar_texto(telefone, mensagem):
    """
    Função de baixo nível: envia uma mensagem de texto simples
    via Graph API para um número de telefone específico.
    Usada tanto pelo MetaSender (disparos agendados) quanto
    pelo webhook (respostas em tempo real).
    """

    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:

        logger.error(
            "WHATSAPP_TOKEN ou WHATSAPP_PHONE_NUMBER_ID "
            "não configurados nas variáveis de ambiente."
        )

        return False

    if not telefone:

        logger.error("Telefone vazio ao tentar enviar mensagem.")

        return False

    payload = {
        "messaging_product": "whatsapp",
        "to": formatar_telefone(telefone),
        "type": "text",
        "text": {
            "body": mensagem
        }
    }

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    try:

        response = requests.post(
            GRAPH_URL,
            json=payload,
            headers=headers,
            timeout=15
        )

    except requests.RequestException as erro:

        logger.error(
            "Falha de conexão ao enviar WhatsApp para %s: %s",
            telefone,
            erro
        )

        return False

    if response.status_code == 200:

        logger.info(
            "Mensagem enviada com sucesso para %s.",
            telefone
        )

        return True

    logger.error(
        "Erro ao enviar WhatsApp para %s: [%s] %s",
        telefone,
        response.status_code,
        response.text
    )

    return False


def enviar_template(telefone, nome_template, idioma, parametros):
    """
    Envia uma mensagem usando um TEMPLATE aprovado pela Meta.

    Diferente de enviar_texto(), isso NÃO depende da janela de 24h estar
    aberta - é o formato correto para mensagens iniciadas pela empresa,
    como os lembretes de cobrança do scheduler.

    `parametros` é uma lista de strings, na ordem das variáveis {{1}},
    {{2}}, {{3}}... definidas no corpo do template aprovado no Meta
    Business Manager.
    """

    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:

        logger.error(
            "WHATSAPP_TOKEN ou WHATSAPP_PHONE_NUMBER_ID "
            "não configurados nas variáveis de ambiente."
        )

        return False

    if not telefone:

        logger.error("Telefone vazio ao tentar enviar template.")

        return False

    payload = {
        "messaging_product": "whatsapp",
        "to": formatar_telefone(telefone),
        "type": "template",
        "template": {
            "name": nome_template,
            "language": {"code": idioma},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(valor)}
                        for valor in parametros
                    ],
                }
            ],
        },
    }

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    try:

        response = requests.post(
            GRAPH_URL,
            json=payload,
            headers=headers,
            timeout=15
        )

    except requests.RequestException as erro:

        logger.error(
            "Falha de conexão ao enviar template WhatsApp para %s: %s",
            telefone,
            erro
        )

        return False

    if response.status_code == 200:

        logger.info(
            "Template '%s' enviado com sucesso para %s.",
            nome_template,
            telefone
        )

        return True

    logger.error(
        "Erro ao enviar template '%s' para %s: [%s] %s",
        nome_template,
        telefone,
        response.status_code,
        response.text
    )

    return False


class MetaSender:

    def enviar_pendentes(self):

        disparos = DisparoWhatsApp.objects.filter(
            status="AGENDADO"
        )

        for disparo in disparos:

            sucesso = self.enviar_mensagem(
                disparo
            )

            if sucesso:

                disparo.status = "ENVIADO"

                disparo.data_envio = (
                    timezone.now()
                )

            else:

                disparo.status = "FALHOU"

            disparo.save()

    def enviar_mensagem(
        self,
        disparo
    ):
        from .models import ConfiguracaoWhatsApp

        associado = disparo.associado

        if not associado.telefone:

            logger.error(
                "Associado %s não possui telefone cadastrado.",
                associado.nome
            )

            return False

        config = ConfiguracaoWhatsApp.objects.filter(ativo=True).first()

        if not config:

            logger.error(
                "Nenhuma ConfiguracaoWhatsApp ativa encontrada - "
                "não é possível montar o template."
            )

            return False

        mensalidade = disparo.mensalidade

        valor = mensalidade.valor if mensalidade else ""
        data_vencimento_obj = (
            getattr(mensalidade, "data_vencimento", None)
            if mensalidade
            else None
        ) or (getattr(mensalidade, "vencimento", None) if mensalidade else None)
        data_vencimento = (
            data_vencimento_obj.strftime("%d/%m/%Y")
            if data_vencimento_obj
            else ""
        )
        chave_pix = config.chave_pix or "Consulte a associação"

        return enviar_template(
            associado.telefone,
            config.nome_template_cobranca,
            config.idioma_template_cobranca,
            [
                associado.nome,
                str(valor),
                data_vencimento,
                chave_pix,
            ],
        )
