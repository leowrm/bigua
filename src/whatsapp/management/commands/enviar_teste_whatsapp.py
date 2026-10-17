import json

import requests
from django.core.management.base import BaseCommand, CommandError

from whatsapp.sender import (
    GRAPH_URL,
    WHATSAPP_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
    formatar_telefone,
)
from whatsapp.models import ConfiguracaoWhatsApp


class Command(BaseCommand):
    """
    Manda uma mensagem de teste direto pela WhatsApp Cloud API, sem
    depender de nenhum dado no banco (Associado, Mensalidade, etc).

    Mostra a resposta bruta da API (status HTTP + JSON), porque um
    status 200 só significa que a Meta ACEITOU a mensagem na fila -
    não garante que ela foi entregue de fato no aparelho do destinatário.

    Uso (texto livre - só entrega se a janela de 24h estiver aberta,
    ou seja, se o destinatário te mandou mensagem primeiro):
        python manage.py enviar_teste_whatsapp --telefone 5551999998888

    Uso (template de cobrança configurado no painel):
        python manage.py enviar_teste_whatsapp --telefone 5551999998888 --template-cobranca
    """

    help = "Envia uma mensagem de teste via WhatsApp Cloud API e mostra a resposta bruta da Meta."

    def add_arguments(self, parser):
        parser.add_argument(
            "--telefone",
            required=True,
            help="Número de destino no formato DDI+DDD+numero, ex: 5551999998888",
        )
        parser.add_argument(
            "--mensagem",
            default="Mensagem de teste do sistema Brisa-Biguá 🐊",
            help="Texto a ser enviado no modo texto livre (ignorado se usar --template).",
        )
        parser.add_argument(
            "--template",
            action="store_true",
            help="Envia o template padrão 'hello_world' em vez de texto livre. "
                 "Não depende da janela de 24h estar aberta.",
        )
        parser.add_argument(
            "--template-cobranca",
            action="store_true",
            help="Envia o template de cobrança configurado no painel, com dados fictícios.",
        )
        parser.add_argument(
            "--parametros",
            default="Associado de teste;R$ 50,00;10/09/2026;pix@exemplo.com",
            help="Valores das variáveis do template, separados por ponto e vírgula e na ordem do template.",
        )

    def handle(self, *args, **options):
        if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
            raise CommandError(
                "WHATSAPP_TOKEN ou WHATSAPP_PHONE_NUMBER_ID não estão "
                "configurados. Confira o arquivo .env na pasta src/."
            )

        telefone = formatar_telefone(options["telefone"])

        if options["template_cobranca"]:
            config = ConfiguracaoWhatsApp.objects.filter(ativo=True).first()
            if not config:
                raise CommandError("Nenhuma configuração ativa do WhatsApp foi encontrada.")
            parametros = [item.strip() for item in options["parametros"].split(";")]
            payload = {
                "messaging_product": "whatsapp",
                "to": telefone,
                "type": "template",
                "template": {
                    "name": config.nome_template_cobranca,
                    "language": {"code": config.idioma_template_cobranca},
                    "components": [{
                        "type": "body",
                        "parameters": [{"type": "text", "text": item} for item in parametros],
                    }],
                },
            }
            self.stdout.write(
                f"Enviando template de cobrança '{config.nome_template_cobranca}' "
                f"({config.idioma_template_cobranca}) para {telefone}..."
            )
        elif options["template"]:
            payload = {
                "messaging_product": "whatsapp",
                "to": telefone,
                "type": "template",
                "template": {
                    "name": "hello_world",
                    "language": {"code": "en_US"},
                },
            }
            self.stdout.write(f"Enviando template 'hello_world' para {telefone}...")
        else:
            payload = {
                "messaging_product": "whatsapp",
                "to": telefone,
                "type": "text",
                "text": {"body": options["mensagem"]},
            }
            self.stdout.write(f"Enviando texto livre para {telefone}...")
            self.stdout.write(
                self.style.WARNING(
                    "Atenção: texto livre só é ENTREGUE se o destinatário "
                    "tiver mandado mensagem pra esse número nas últimas 24h. "
                    "A Meta pode retornar sucesso (200) e mesmo assim não entregar."
                )
            )

        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        response = requests.post(GRAPH_URL, json=payload, headers=headers, timeout=15)

        self.stdout.write(f"\nStatus HTTP: {response.status_code}")
        self.stdout.write("Resposta da Meta:")
        try:
            self.stdout.write(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except ValueError:
            self.stdout.write(response.text)

        if response.status_code == 200:
            self.stdout.write(self.style.SUCCESS(
                "\nA Meta aceitou a mensagem (retornou um message id acima). "
                "Isso NÃO garante entrega - confira o WhatsApp do destinatário "
                "e, se não chegar, veja o motivo no painel da Meta "
                "(WhatsApp Manager > seu número > Insights) ou tente com --template."
            ))
        else:
            raise CommandError(
                "\nA Meta recusou a mensagem. Veja o campo 'error' acima "
                "(costuma indicar código e descrição exatos do problema)."
            )
