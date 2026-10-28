from urllib.parse import urlsplit

from django.contrib.auth.models import Permission, User
from django.test import TestCase

from buiga_utils import cpf_valido

from .models import Associado, Alunos, Mensalidades, Planos


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


class PermissoesEAcoesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="associado-teste",
            password="SenhaForte123!",
        )
        self.plano = Planos.objects.create(
            nome_plano="Plano teste",
            valor="10.00",
            meses_antecipados=1,
            regime_cobranca="mensal",
        )
        self.associado = Associado.objects.create(
            nome="Pessoa Teste",
            cpf="52998224725",
            nascimento="1990-01-01",
            email="pessoa@example.com",
            telefone="51999999999",
            dia_cobranca=10,
            estado="Ativo",
            id_planos=self.plano,
        )
        self.aluno = Alunos.objects.create(
            nome="Aluno Teste",
            cpf="39053344705",
            nascimento="2010-01-01",
            escola="Escola Teste",
            serie="5º ano",
        )
        self.client.force_login(self.user)

    def test_usuario_sem_staff_nao_acessa_dashboard(self):
        response = self.client.get("/v1/dashboard/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlsplit(response["Location"]).path, "/v1/app/")

    def test_permissao_de_projeto_exibe_menu_sem_permissao_de_patrimonio(self):
        permissao = Permission.objects.get(
            codename="view_projeto",
            content_type__app_label="v1",
        )
        self.user.user_permissions.add(permissao)

        response = self.client.get("/v1/app/", follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="nav-projetos"')

    def test_exclusao_de_associado_exige_post(self):
        permissao = Permission.objects.get(
            codename="view_associado",
            content_type__app_label="v1",
        )
        self.user.user_permissions.add(permissao)

        response = self.client.get(
            f"/v1/associado/excluir/{self.associado.id_associado}"
        )

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Associado.objects.filter(pk=self.associado.pk).exists())

    def test_exclusao_de_aluno_exige_post(self):
        permissao = Permission.objects.get(
            codename="view_projeto",
            content_type__app_label="v1",
        )
        self.user.user_permissions.add(permissao)

        response = self.client.get(f"/v1/alunos/excluir/{self.aluno.id_aluno}/")

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Alunos.objects.filter(pk=self.aluno.pk).exists())

    def test_confirmacao_de_associado_so_cria_mensalidade_no_post(self):
        permissao = Permission.objects.get(
            codename="view_associado",
            content_type__app_label="v1",
        )
        self.user.user_permissions.add(permissao)

        response = self.client.get(
            f"/v1/associado/{self.associado.id_associado}/confirmar"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Mensalidades.objects.count(), 0)

        response = self.client.post(
            f"/v1/associado/{self.associado.id_associado}/confirmar",
            {"acao": "confirmar"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Mensalidades.objects.count(), 1)

        self.client.post(
            f"/v1/associado/{self.associado.id_associado}/confirmar",
            {"acao": "confirmar"},
        )
        self.assertEqual(Mensalidades.objects.count(), 1)
