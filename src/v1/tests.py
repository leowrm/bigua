from django.contrib.auth.models import Permission, User
from django.test import TestCase

from buiga_utils import cpf_valido

from .models import Planos


class CadastroAssociadoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin-teste",
            password="SenhaForte123!",
            is_staff=True,
        )
        permission = Permission.objects.get(
            codename="view_associado",
            content_type__app_label="v1",
        )
        self.user.user_permissions.add(permission)
        Planos.objects.create(
            nome_plano="Plano teste",
            valor="10.00",
            meses_antecipados=1,
            regime_cobranca="mensal",
        )
        self.client.force_login(self.user)

    def test_cpf_valido_rejeita_numero_invalido(self):
        self.assertFalse(cpf_valido("111.111.111-11"))

    def test_cadastro_preserva_dados_quando_cpf_e_invalido(self):
        response = self.client.post(
            "/v1/associado/novo/",
            {
                "nome": "Pessoa Teste",
                "cpf": "111.111.111-11",
                "telefone": "51999999999",
                "email": "pessoa@example.com",
                "nascimento": "1990-01-01",
                "dia_cobranca": "10",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Pessoa Teste"')
        self.assertContains(response, 'value="111.111.111-11"')
        self.assertContains(response, 'input-error')
        self.assertContains(response, "CPF inválido.")


class HealthCheckTests(TestCase):
    def test_health_check_returns_ok(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
