from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.db.models import Max

from .services import WhatsAppService
from .scheduler import CobrancaScheduler
from .models import (
    ConfiguracaoWhatsApp,
    DisparoWhatsApp,
    ConversaWhatsApp,
    EstadoConversa,
    TemplateWhatsApp,
)
from .template_manager import (
    TemplateManagerError,
    criar_template,
    editar_template,
    sincronizar_templates,
)


def _pode_acessar_whatsapp(user):
    return user.is_staff or user.has_perm("whatsapp.view_configuracaowhatsapp")


@login_required(login_url="/v1/login/")
@user_passes_test(_pode_acessar_whatsapp, login_url="/v1/app/")
def teste_bot(request):

    texto = request.GET.get("msg", "")
    telefone = request.GET.get("telefone", "51999999999")

    bot = WhatsAppService()

    associado = bot.buscar_associado_por_telefone(
        telefone
    )

    bot.salvar_mensagem(
        telefone=telefone,
        mensagem=texto,
        direcao="RECEBIDA",
        associado=associado
    )

    resposta = bot.processar_mensagem(texto, telefone)

    bot.salvar_mensagem(
        telefone=telefone,
        mensagem=resposta,
        direcao="ENVIADA",
        associado=associado
    )

    return JsonResponse({
        "resposta": resposta
    })
    
@login_required(login_url="/v1/login/")
@user_passes_test(_pode_acessar_whatsapp, login_url="/v1/app/")
def painel_conversas(request):
    """
    Painel (somente leitura) para o voluntário acompanhar as
    conversas reais entre os associados e o bot do WhatsApp -
    estilo caixa de entrada, com lista de conversas à esquerda e o
    histórico de mensagens à direita.
    """

    telefones = (
        ConversaWhatsApp.objects
        .values("telefone")
        .annotate(ultima=Max("data_hora"))
        .order_by("-ultima")
    )

    telefone_selecionado = request.GET.get("telefone", "")

    conversas = []

    estados = {
        e.telefone: e.estado
        for e in EstadoConversa.objects.all()
    }

    for item in telefones:

        telefone = item["telefone"]

        ultima_msg = (
            ConversaWhatsApp.objects
            .filter(telefone=telefone)
            .order_by("-data_hora")
            .select_related("associado")
            .first()
        )

        if not ultima_msg:
            continue

        conversas.append({
            "telefone": telefone,
            "associado": ultima_msg.associado,
            "ultima_mensagem": ultima_msg.mensagem,
            "ultima_data": ultima_msg.data_hora,
            "estado": estados.get(telefone, "MENU"),
            "aguardando_humano": estados.get(telefone) == "HUMANO",
        })

        if not telefone_selecionado:
            telefone_selecionado = telefone

    mensagens_selecionadas = []

    if telefone_selecionado:
        mensagens_selecionadas = list(
            ConversaWhatsApp.objects
            .filter(telefone=telefone_selecionado)
            .order_by("data_hora")
        )

    return render(request, "whatsapp/conversas.html", {
        "conversas": conversas,
        "telefone_selecionado": telefone_selecionado,
        "mensagens": mensagens_selecionadas,
    })


@login_required(login_url="/v1/login/")
@user_passes_test(_pode_acessar_whatsapp, login_url="/v1/app/")
def testar_scheduler(request):

    scheduler = CobrancaScheduler()

    scheduler.executar()

    return JsonResponse({
        "status": "scheduler executado"
    })


@login_required(login_url="/v1/login/")
@user_passes_test(_pode_acessar_whatsapp, login_url="/v1/app/")
def painel_configuracao(request):
    """
    Tela onde os administradores da ONG configuram os lembretes de
    cobrança do WhatsApp: quantos dias antes/depois do vencimento
    disparar, o texto de cada mensagem, a chave Pix e o template
    aprovado usado no envio.
    """

    config = ConfiguracaoWhatsApp.objects.filter(ativo=True).first()

    if not config:
        config = ConfiguracaoWhatsApp.objects.create(ativo=True)

    if request.method == "POST":

        config.dias_aviso_antes = request.POST.get(
            "dias_aviso_antes", config.dias_aviso_antes
        )
        config.dias_aviso_atraso = request.POST.get(
            "dias_aviso_atraso", config.dias_aviso_atraso
        )
        config.chave_pix = request.POST.get("chave_pix", "")
        config.numero_atendimento_humano = request.POST.get(
            "numero_atendimento_humano", ""
        )
        config.mensagem_aviso_antes = request.POST.get(
            "mensagem_aviso_antes", ""
        )
        config.mensagem_vencimento = request.POST.get(
            "mensagem_vencimento", ""
        )
        config.mensagem_aviso_atraso = request.POST.get(
            "mensagem_aviso_atraso", ""
        )
        config.nome_template_cobranca = request.POST.get(
            "nome_template_cobranca", config.nome_template_cobranca
        )
        config.idioma_template_cobranca = request.POST.get(
            "idioma_template_cobranca", config.idioma_template_cobranca
        )
        config.ativo = request.POST.get("ativo") == "on"

        config.save()

        messages.success(request, "Configuração do WhatsApp salva com sucesso.")

        return redirect("whatsapp-configuracao")

    return render(request, "whatsapp/configuracao.html", {
        "config": config,
    })


@login_required(login_url="/v1/login/")
@user_passes_test(_pode_acessar_whatsapp, login_url="/v1/app/")
def painel_historico(request):
    """
    Tela com o histórico de disparos do WhatsApp (agendados, enviados
    e que falharam), com botões para gerar e enviar os disparos
    pendentes sem precisar usar o terminal.
    """

    if request.method == "POST":

        acao = request.POST.get("acao")

        if acao == "gerar":
            CobrancaScheduler().executar()
            messages.success(request, "Disparos gerados com base nas mensalidades pendentes.")

        elif acao == "enviar":
            from .sender import MetaSender
            MetaSender().enviar_pendentes()
            messages.success(request, "Envio dos disparos agendados processado.")

        return redirect("whatsapp-historico")

    status_filtro = request.GET.get("status", "")

    disparos = DisparoWhatsApp.objects.select_related(
        "associado", "mensalidade"
    ).order_by("-data_programada")

    if status_filtro:
        disparos = disparos.filter(status=status_filtro)

    disparos = disparos[:200]

    contagens = {
        "AGENDADO": DisparoWhatsApp.objects.filter(status="AGENDADO").count(),
        "ENVIADO": DisparoWhatsApp.objects.filter(status="ENVIADO").count(),
        "FALHOU": DisparoWhatsApp.objects.filter(status="FALHOU").count(),
    }

    return render(request, "whatsapp/historico.html", {
        "disparos": disparos,
        "contagens": contagens,
        "status_filtro": status_filtro,
    })


@login_required(login_url="/v1/login/")
@user_passes_test(_pode_acessar_whatsapp, login_url="/v1/app/")
def painel_templates(request):
    if request.method == "POST":
        acao = request.POST.get("acao")
        try:
            if acao == "sincronizar":
                sincronizar_templates()
                messages.success(request, "Templates sincronizados com a Meta.")
            elif acao == "criar":
                nome = request.POST.get("nome", "").strip()
                idioma = request.POST.get("idioma", "pt_BR").strip()
                categoria = request.POST.get("categoria", "UTILITY").strip().upper()
                corpo = request.POST.get("corpo", "").strip()
                exemplos = [item.strip() for item in request.POST.get("exemplos", "").split(",") if item.strip()]
                if not nome or not corpo:
                    raise TemplateManagerError("Nome e corpo do template são obrigatórios.")
                criar_template(nome, idioma, categoria, corpo, exemplos or None)
                messages.success(request, "Template enviado para análise da Meta.")
        except TemplateManagerError as exc:
            messages.error(request, str(exc))
        return redirect("whatsapp-templates")

    config = ConfiguracaoWhatsApp.objects.filter(ativo=True).first()
    return render(request, "whatsapp/templates.html", {
        "templates_meta": TemplateWhatsApp.objects.all(),
        "template_cobranca": config.nome_template_cobranca if config else "",
        "idioma_cobranca": config.idioma_template_cobranca if config else "pt_BR",
    })


@login_required(login_url="/v1/login/")
@user_passes_test(_pode_acessar_whatsapp, login_url="/v1/app/")
def painel_template_editar(request, template_id):
    template = TemplateWhatsApp.objects.get(pk=template_id)
    if request.method == "POST":
        try:
            corpo = request.POST.get("corpo", "").strip()
            categoria = request.POST.get("categoria", template.categoria).strip().upper()
            exemplos = [item.strip() for item in request.POST.get("exemplos", "").split(",") if item.strip()]
            if not corpo:
                raise TemplateManagerError("O corpo do template é obrigatório.")
            editar_template(template, corpo, categoria, exemplos or None)
            messages.success(request, "Alteração enviada para análise da Meta.")
        except TemplateManagerError as exc:
            messages.error(request, str(exc))
        return redirect("whatsapp-templates")
    body = next((item for item in (template.componentes or []) if item.get("type", "").upper() == "BODY"), {})
    exemplos = ((body.get("example") or {}).get("body_text") or [[]])[0]
    return render(request, "whatsapp/template_editar.html", {"template_meta": template, "exemplos": ", ".join(exemplos)})


@login_required(login_url="/v1/login/")
@user_passes_test(_pode_acessar_whatsapp, login_url="/v1/app/")
def painel_template_usar(request, template_id):
    if request.method == "POST":
        template = TemplateWhatsApp.objects.get(pk=template_id)
        config = ConfiguracaoWhatsApp.objects.filter(ativo=True).first()
        if not config:
            config = ConfiguracaoWhatsApp.objects.create(ativo=True)
        config.nome_template_cobranca = template.nome
        config.idioma_template_cobranca = template.idioma
        config.save(update_fields=["nome_template_cobranca", "idioma_template_cobranca", "atualizado_em"] if hasattr(config, "atualizado_em") else ["nome_template_cobranca", "idioma_template_cobranca"])
        messages.success(request, f"Template '{template.nome}' selecionado para as cobranças.")
    return redirect("whatsapp-templates")
