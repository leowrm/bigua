import json
import logging
import os

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .sender import enviar_texto
from .services import WhatsAppService

logger = logging.getLogger(__name__)

WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN")


@csrf_exempt
def webhook(request):

    if request.method == "GET":
        return _verificar_webhook(request)

    if request.method == "POST":
        return _receber_webhook(request)

    return HttpResponse(status=405)


def _verificar_webhook(request):
    """
    Endpoint chamado pela Meta ao configurar o webhook
    (validação do hub.challenge).
    """

    modo = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    desafio = request.GET.get("hub.challenge")

    if modo == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return HttpResponse(desafio)

    logger.warning("Falha na verificação do webhook do WhatsApp.")

    return HttpResponse(status=403)


def _receber_webhook(request):
    """
    Endpoint chamado pela Meta a cada mensagem recebida.
    """

    try:
        dados = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):

        logger.error("Payload inválido recebido no webhook do WhatsApp.")

        return JsonResponse({"status": "erro"}, status=400)

    bot = WhatsAppService()

    try:

        for entrada in dados.get("entry", []):
            for change in entrada.get("changes", []):

                valor = change.get("value", {})
                mensagens = valor.get("messages", [])

                for mensagem in mensagens:

                    telefone = mensagem.get("from")
                    texto = mensagem.get("text", {}).get("body", "")

                    if not telefone:
                        continue

                    associado = bot.buscar_associado_por_telefone(
                        telefone
                    )

                    bot.salvar_mensagem(
                        telefone=telefone,
                        mensagem=texto,
                        direcao="RECEBIDA",
                        associado=associado
                    )

                    resposta = bot.processar_mensagem(
                        texto,
                        telefone
                    )

                    bot.salvar_mensagem(
                        telefone=telefone,
                        mensagem=resposta,
                        direcao="ENVIADA",
                        associado=associado
                    )

                    enviar_texto(telefone, resposta)

    except Exception:

        logger.exception(
            "Erro ao processar webhook do WhatsApp."
        )

    # Sempre responder 200 rápido, senão a Meta reenvia o evento
    return JsonResponse({"status": "recebido"})