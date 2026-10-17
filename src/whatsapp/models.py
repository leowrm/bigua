from django.db import models
from v1.models import Associado


class ConversaWhatsApp(models.Model):

    DIRECOES = [
        ("ENVIADA", "Enviada"),
        ("RECEBIDA", "Recebida"),
    ]

    associado = models.ForeignKey(Associado, on_delete=models.SET_NULL, null=True, blank=True)

    telefone = models.CharField(max_length=20)

    mensagem = models.TextField()

    direcao = models.CharField(max_length=10, choices=DIRECOES)

    data_hora = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.telefone} - {self.direcao}"


class EstadoConversa(models.Model):

    telefone = models.CharField(max_length=20, unique=True)

    estado = models.CharField(max_length=50, default="MENU")

    ultima_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.telefone} - {self.estado}"


class DisparoWhatsApp(models.Model):

    STATUS = [
        ("AGENDADO", "Agendado"),
        ("ENVIADO", "Enviado"),
        ("FALHOU", "Falhou"),
    ]

    TIPOS = [
        ("PRE_VENCIMENTO", "Pré-vencimento"),
        ("VENCIMENTO", "Vencimento"),
        ("ATRASO", "Atraso"),
    ]

    associado = models.ForeignKey(Associado, on_delete=models.CASCADE)

    mensagem = models.TextField()

    status = models.CharField(max_length=20, choices=STATUS, default="AGENDADO")

    tipo = models.CharField(max_length=30, choices=TIPOS, default="PRE_VENCIMENTO")

    data_programada = models.DateTimeField()

    data_envio = models.DateTimeField(null=True, blank=True)

    mensalidade = models.ForeignKey(
        "v1.Mensalidades",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.associado.nome} - {self.status}"


class ConfiguracaoWhatsApp(models.Model):

    dias_aviso_antes = models.IntegerField(default=3)

    dias_aviso_atraso = models.IntegerField(default=3)

    numero_atendimento_humano = models.CharField(max_length=20, blank=True)

    chave_pix = models.CharField(max_length=255, blank=True)

    mensagem_aviso_antes = models.TextField(blank=True)

    mensagem_vencimento = models.TextField(blank=True)

    mensagem_aviso_atraso = models.TextField(blank=True)

    nome_template_cobranca = models.CharField(
        max_length=100,
        default="lembrete_mensalidade_bigua",
        help_text="Nome exato do template aprovado no Meta Business Manager "
                   "usado para os lembretes de cobrança (pré-vencimento, "
                   "vencimento e atraso).",
    )

    idioma_template_cobranca = models.CharField(
        max_length=10,
        default="pt_BR",
        help_text="Código de idioma do template, exatamente como cadastrado "
                   "na Meta (ex: pt_BR).",
    )

    ativo = models.BooleanField(default=True)

    tipo = models.CharField(max_length=30, default="PRE_VENCIMENTO")

    def __str__(self):
        return "Configuração WhatsApp"


class TemplateWhatsApp(models.Model):
    """Cópia local dos templates administrados na WhatsApp Cloud API."""

    STATUS = [
        ("PENDING", "Pendente"),
        ("APPROVED", "Aprovado"),
        ("REJECTED", "Rejeitado"),
        ("PAUSED", "Pausado"),
        ("DISABLED", "Desativado"),
        ("UNKNOWN", "Desconhecido"),
    ]

    meta_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    nome = models.CharField(max_length=100)
    idioma = models.CharField(max_length=20, default="pt_BR")
    categoria = models.CharField(max_length=30, default="UTILITY")
    corpo = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS, default="UNKNOWN")
    componentes = models.JSONField(default=list, blank=True)
    ultima_sincronizacao = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["nome", "idioma"],
                name="whatsapp_template_nome_idioma_unico",
            )
        ]
        ordering = ["nome", "idioma"]

    def __str__(self):
        return f"{self.nome} ({self.idioma})"
