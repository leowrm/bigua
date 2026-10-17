from unittest.mock import patch

from django.test import TestCase

from v1.models import Associado, Mensalidades, Planos

from .models import ConversaWhatsApp, EstadoConversa
from .services import WhatsAppService


class WhatsAppWebhookTests(TestCase):
    @patch("whatsapp.webhooks.WHATSAPP_VERIFY_TOKEN", "token-de-teste")
    def test_meta_consegue_validar_webhook(self):
        response = self.client.get(
            "/whatsapp/webhook/",
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "token-de-teste",
                "hub.challenge": "123456",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"123456")

    @patch("whatsapp.webhooks.enviar_texto", return_value=True)
    def test_webhook_registra_mensagem_e_resposta_sem_chamar_meta_real(self, enviar):
        response = self.client.post(
            "/whatsapp/webhook/",
            data={
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "from": "5551999999999",
                                "text": {"body": "oi"},
                            }]
                        }
                    }]
                }]
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ConversaWhatsApp.objects.count(), 2)
        self.assertEqual(EstadoConversa.objects.get(telefone="5551999999999").estado, "MENU")
        enviar.assert_called_once()


class WhatsAppMenuTests(TestCase):
    def setUp(self):
        plano = Planos.objects.create(
            nome_plano="Plano teste",
            valor="25.00",
            meses_antecipados=1,
            regime_cobranca="mensal",
        )
        self.associado = Associado.objects.create(
            nome="Pessoa WhatsApp",
            cpf="52998224725",
            nascimento="1990-01-01",
            email="whatsapp@example.com",
            telefone="5551999999999",
            dia_cobranca=10,
            estado="Ativo",
            id_planos=plano,
        )

    def test_menu_consulta_todas_as_mensalidades_abertas(self):
        Mensalidades.objects.create(
            id_associado=self.associado,
            vencimento="2026-09-10",
            periodo_referencia="2026-09-01",
            id_planos=self.associado.id_planos,
            valor="25.00",
            estado_pagamento="Pendente",
        )
        Mensalidades.objects.create(
            id_associado=self.associado,
            vencimento="2026-10-10",
            periodo_referencia="2026-10-01",
            id_planos=self.associado.id_planos,
            valor="25.00",
            estado_pagamento="Atrasado",
        )

        resposta = WhatsAppService().processar_mensagem("1", self.associado.telefone)

        self.assertIn("10/09/2026", resposta)
        self.assertIn("10/10/2026", resposta)

    def test_menu_doacao_exibe_chave_pix_fixa(self):
        from .models import ConfiguracaoWhatsApp

        ConfiguracaoWhatsApp.objects.create(chave_pix="doacoes@bigua.org", ativo=True)

        resposta = WhatsAppService().processar_mensagem("2", self.associado.telefone)

        self.assertIn("doacoes@bigua.org", resposta)
