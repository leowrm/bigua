from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import Permission, User
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.shortcuts import redirect
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum, F, ExpressionWrapper, DecimalField
from django.db.models.functions import ExtractMonth, ExtractDay
from .models import *
import decimal
import buiga_utils
import datetime
import re


# Create your views here.
def index(request):
    return redirect("login")


def landing(request):
    return render(request, "landing.html")

#------ Production only ------#
producao = False
if producao:
    Associado.objects.all().delete()
    Planos.objects.all().delete()
#-----------------------------#

def loginPanel(request):
    if request.method == "GET":
        return render(request, "login.html")
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("app")
        else:
            messages.error(request, "Usuário ou senha inválida")
            return redirect("login")


def logoutPanel(request):
    logout(request)
    return redirect("login")

@login_required(login_url="/v1/login/")
@user_passes_test(lambda u: u.is_staff, login_url="/v1/app/")
def registerPanel(request):
    if request.method == "GET":
        return render(request, "cadastro.html")
    else:
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = User.objects.filter(username=username).first()
        if user:
            return HttpResponse("Username already exists.", status=400)

        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        user.save()

        return HttpResponse(f"Username: {username}, Email: {email}")


@login_required(login_url="/v1/login/")
def app(request):
    return redirect("dashboard")

@login_required(login_url="/v1/login/")
def dashboardPanel(request):
    receitas_mes = Mensalidades.objects.filter(
            vencimento__year=datetime.datetime.now().year,
            vencimento__month=datetime.datetime.now().month,
            )
    inadimplentes = receitas_mes.filter(estado_pagamento="Atrasado").count() or 0
    receita_mensal_esperada = receitas_mes.exclude(estado_pagamento="Cancelado").aggregate(total=Sum('valor'))['total'] or 0
    historico_receita = (
        Mensalidades.objects
            .filter(
                estado_pagamento="Pago",
                vencimento__gte=(datetime.datetime.today() - datetime.timedelta(days=180))
            )
            .values("periodo_referencia")
            .annotate(total_pago=Sum("valor"))
            .order_by("periodo_referencia")
        )
        # Descobre o maior valor pago
    max_pago = max([receita["total_pago"] for receita in historico_receita], default=0)

    # Adiciona percentual em cada item
    for receita in historico_receita:
        if max_pago > 0:
            receita["percentual"] = (receita["total_pago"] / max_pago) * 90
        else:
            receita["percentual"] = 0

    aniversariantes = (
        Associado.objects
        .annotate(
            mes=ExtractMonth("nascimento"),
            dia=ExtractDay("nascimento")
        )
        # Filtrar aniversários que ainda vão acontecer neste ano
        .filter(
            mes__gt=datetime.date.today().month
        ) | Associado.objects.annotate(
            mes=ExtractMonth("nascimento"),
            dia=ExtractDay("nascimento")
        ).filter(
            mes=datetime.date.today().month,
            dia__gte=datetime.date.today().day
        )
    ).order_by("mes", "dia")[:2]

    projetos = (
        Projeto.objects.filter(estado="Em andamento")
        .annotate(
            total_gasto=Sum("movimentacaofinanceira__valor") or 0,
        )
        .annotate(
        percentual_gasto=ExpressionWrapper(
            (F("total_gasto") / F("valor")) * 100,
            output_field=DecimalField(max_digits=2, decimal_places=2)
            )
        )
        .order_by("-data_inicio")
    )

    for projeto in projetos:
        total = projeto.total_gasto or 0
        if projeto.valor > 0:
            projeto.percentual = (total / projeto.valor) * 100
        else:
            projeto.percentual = 0

    infomacoes = {
        "associados_ativos": Associado.objects.filter(estado="Ativo").count(),
        "receita_mensal_esperada": receita_mensal_esperada,
        "receita_mes": (receitas_mes.filter(estado_pagamento="Pago").aggregate(total=Sum('valor'))['total']),
        "inadimplentes": inadimplentes,
        "percentual_inadimplentes": (inadimplentes / (receitas_mes.count() or 1)) * 100,
        "cobrancas": receitas_mes.count(),
        "cobrancas_abertas": receitas_mes.filter(estado_pagamento="Pendente").count(),
        "historico_receitas": historico_receita,
        "aniversariantes": aniversariantes,
        "projetos": projetos
    }
    return render(request, "dashboard.html", infomacoes)


@login_required()
@permission_required('v1.view_associado', login_url="/v1/app/")
def associados(request):
    return render(request, "associados.html", {"associados": Associado.objects.all(), "responsaveis": ResponsavelFinanceiro.objects.all()})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_associado', login_url="/v1/app/")
def filtroAssociados(request):
    if request.method == "POST":
        filtro = request.POST.get("busca")
        associados = Associado.objects.filter(nome__icontains=filtro) | Associado.objects.filter(cpf__icontains=filtro)
        return render(request, "associados.html", {"associados": associados})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_associado', login_url="/v1/app/")
def novoAssociado(request):
    if request.method == "GET":
        return render(request, "novo-associado.html")
    else:
        nome = request.POST.get("nome")
        cpf = request.POST.get("cpf")
        telefone = request.POST.get("telefone")
        email = request.POST.get("email")
        nascimento = request.POST.get("nascimento")
        dia_cobranca = request.POST.get("dia_cobranca")

        form_data = {
            "nome": nome or "",
            "cpf": cpf or "",
            "telefone": telefone or "",
            "email": email or "",
            "nascimento": nascimento or "",
            "dia_cobranca": dia_cobranca or "",
        }

        def erro_formulario(mensagem, campo=None):
            messages.error(request, mensagem)
            return render(request, "novo-associado.html", {
                "form_data": form_data,
                "invalid_field": campo,
            })

        if Planos.objects.count() == 0:
            Planos.objects.create(
                nome_plano="Grátis",
                valor=decimal.Decimal("0.00"),
                meses_antecipados=1,
                aceita_dinheiro=True,
                aceita_pix=True,
                regime_cobranca="mensal",
                estado=True
            ).save()

        #Validações
        if not nome or re.search(r'^[A-Za-zÀ-ÖØ-öø-ÿ\s]+$', nome) is None:
            return erro_formulario("Nome inválido", "nome")
        if not cpf or not buiga_utils.cpf_valido(cpf):
            return erro_formulario("CPF inválido.", "cpf")
        else:
            cpf = "".join(filter(str.isdigit, cpf))
        if not telefone or len(telefone) != 11:
            return erro_formulario("Telefone precisa ter 11 dígitos.", "telefone")
        if not email or re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is None:
            return erro_formulario("Email inválido.", "email")
        if Associado.objects.filter(cpf=cpf).exists():
            return erro_formulario("CPF já cadastrado.", "cpf")
        if not nascimento or not buiga_utils.validar_data(nascimento):
            return erro_formulario("Data inválida", "nascimento")
        if not nome or not cpf or not telefone or not email or not nascimento or not dia_cobranca:
            return erro_formulario("Todos os campos são obrigatórios.")
        if datetime.datetime.strptime(nascimento, "%Y-%m-%d").date() > datetime.date.today():
            return erro_formulario("Data de nascimento não pode ser no futuro", "nascimento")
        
        associado = Associado.objects.create(
            nome=nome,
            cpf=cpf,
            nascimento=nascimento,
            email=email,
            telefone=telefone,
            dia_cobranca=dia_cobranca,
            estado="Ativo",
            id_planos=Planos.objects.first()
        )
        associado.save()

        ResponsavelFinanceiro.objects.create(
            id_associado=associado,
            id_responsavel=associado
        ).save()

        return redirect(
            "vincular-responsavel", id_associado=associado.id_associado, id_responsavel=associado.id_associado
        )

@login_required(login_url="/v1/login/")
@permission_required('v1.view_associado', login_url="/v1/app/")
def editarAssociadoPanel(request, id_associado):
    associado = Associado.objects.filter(id_associado=id_associado).first()
    if not associado:
        return HttpResponse("Associado não encontrado.", status=404)

    if request.method == "GET":
        responsavel = ResponsavelFinanceiro.objects.filter(id_associado=associado).first().id_responsavel
        return render(request, "editar-associado.html", {"associado": associado, "responsavel": responsavel, "planos": Planos.objects.all()})
    else:
        nome = request.POST.get("nome")
        telefone = request.POST.get("telefone")
        email = request.POST.get("email")
        nascimento = request.POST.get("nascimento")
        dia_cobranca = request.POST.get("dia_cobranca")

        if re.search(r'^[A-Za-zÀ-ÖØ-öø-ÿ\s]+$', nome) is None:
            messages.error(request, "Nome inválido")
            return redirect("editar-associado", id_associado=id_associado)
        if not buiga_utils.validar_data(nascimento):
            messages.error(request, "Data inválida")
            return redirect("editar-associado", id_associado=id_associado)
        if not nome or not telefone or not email or not nascimento or not dia_cobranca:
            messages.error(request, "Todos os campos são obrigatórios.")
            return redirect("editar-associado", id_associado=id_associado)
        if datetime.datetime.strptime(nascimento, "%Y-%m-%d").date() > datetime.date.today():
            messages.error(request, "Data de nascimento não pode ser no futuro")
            return redirect("editar-associado", id_associado=id_associado)
        if len(telefone) != 11:
            messages.error(request, "Telefone precisa ter 11 dígitos.")    
            return redirect("editar-associado", id_associado=id_associado)
        if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is None:
            messages.error(request, "Email inválido.")
            return redirect("editar-associado", id_associado=id_associado)

        Associado.objects.filter(id_associado=id_associado).update(
            nome=nome,
            telefone=telefone,
            email=email,
            nascimento=nascimento,
            dia_cobranca=dia_cobranca
        )
        return redirect("associados")
    
@login_required(login_url="/v1/login/")
@permission_required('v1.view_associado', login_url="/v1/app/")
def confirmarInativacao(request, id_associado):
    associado = Associado.objects.get(id_associado=id_associado)
    return render(request, "confirmar-inativacao.html", {"associado": associado})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_associado', login_url="/v1/app/")
def confirmarReativacao(request, id_associado):
    associado = Associado.objects.get(id_associado=id_associado)
    return render(request, "confirmar-reativacao.html", {"associado": associado})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_associado', login_url="/v1/app/")
def reativarAssociado(request, id_associado):
    associado = Associado.objects.get(id_associado=id_associado)
    associado.estado = "Ativo"
    associado.save()

    for i in range(Planos.objects.get(id_plano=associado.id_planos.id_plano).meses_antecipados):
        Mensalidades.objects.create(
            id_associado = associado,
            data_pagamento = None,
            vencimento = datetime.datetime.today(),
            periodo_referencia = buiga_utils.calcular_periodo_referencia(associado.id_planos.regime_cobranca, i),
            id_planos = associado.id_planos,
            valor = associado.id_planos.valor,
            estado_pagamento = "Pendente"
        )
    return redirect("associados")

@login_required(login_url="/v1/login/")
@permission_required('v1.view_associado', login_url="/v1/app/")
def inativarAssociado(request, id_associado):
    associado = Associado.objects.get(id_associado=id_associado)
    associado.estado = "Inativo"
    associado.save()

    for cobranca in Mensalidades.objects.filter(id_associado=associado):
        cobranca.estado_pagamento = "Cancelado"
        cobranca.save()

    return redirect("associados")

@login_required(login_url="/v1/login/")
@permission_required('v1.view_associado', login_url="/v1/app/")
def excluirAssociado(request, id_associado):
    associado = Associado.objects.get(id_associado=id_associado)
    associado.delete()
    return redirect("associados")

@login_required(login_url="/v1/login/")
@permission_required('v1.view_associado', login_url="/v1/app/")
def vincularResponsavelFinanceiro(request, id_associado, id_responsavel):
    responsavel = Associado.objects.filter(id_associado=id_responsavel).first()
    associado = Associado.objects.filter(id_associado=id_associado).first()
    if not responsavel:
        messages.error(request, "Responsável financeiro não encontrado.")
        return redirect("vincular-responsavel", id_associado, id_responsavel)

    if request.method == "GET":
        return render(
            request,
            "vincular-responsavel-financeiro.html",
            {"responsavel": responsavel, "associado": associado},
        )
    
    elif request.method == "POST":
        if id_associado != id_responsavel:
            Associado.objects.filter(id_associado=id_associado).update(responsavel=False)
        else:
            Associado.objects.filter(id_associado=id_associado).update(responsavel=True)
        
        responsavel = ResponsavelFinanceiro.objects.filter(id_associado=id_associado).first()
        responsavel.id_responsavel = Associado.objects.filter(id_associado=id_responsavel).first()
        responsavel.save()

        return redirect(
            "vincular-plano",
            id_associado=id_associado,
        )


@login_required(login_url="/v1/login/")
@permission_required('v1.view_associado', login_url="/v1/app/")
def buscarResponsavelPanel(request, id_associado):
    cpf = request.POST.get("cpf")
    if request.method == "POST":
        responsavel = Associado.objects.filter(cpf=cpf).first()
        if not responsavel:
            messages.error(request, "CPF do Responsável não encontrado.")
            responsabilidade = ResponsavelFinanceiro.objects.get(id_associado=id_associado)
            return redirect("vincular-responsavel", id_associado, responsabilidade.id_responsavel.id_associado)
        
        return redirect(
            "vincular-responsavel",
            id_associado=id_associado,
            id_responsavel=responsavel.id_associado,
        )

@login_required(login_url="/v1/login/")
@permission_required('v1.view_associado', login_url="/v1/app/")
def buscarEdicaoResponsavelPanel(request, id_associado):
    cpf = request.POST.get("cpf")
    if request.method == "POST":
        responsavel = Associado.objects.filter(cpf=cpf).first()
        if not responsavel:
            responsavel = ResponsavelFinanceiro.objects.get(id_associado=id_associado).id_responsavel
            #responsavel = ResponsavelFinanceiro.objects.filter(id_associado=id_associado).first().id_responsavel
            messages.error(request, "CPF do Responsável não encontrado.")
            return redirect("editar-responsavel-financeiro", 
                            id_associado=id_associado,
                            id_responsavel=responsavel.id_associado)

        return redirect(
            "editar-responsavel-financeiro", 
            id_associado=id_associado,
            id_responsavel=responsavel.id_associado)

@login_required(login_url="/v1/login/")
@permission_required('v1.view_associado', login_url="/v1/app/")
def editarResponsavelFinanceiro(request, id_associado, id_responsavel):
    associado = Associado.objects.filter(id_associado=id_associado).first()
    responsavel = Associado.objects.filter(id_associado=id_responsavel).first()
    if request.method == "GET":
        return render(
            request,
            "editar-responsavel-financeiro.html",
            {"responsavel": responsavel, 
             "associado": associado},
        )
    
    elif request.method == "POST":
        if id_associado != id_responsavel:
            Associado.objects.filter(id_associado=id_associado).update(responsavel=False)
        else:
            Associado.objects.filter(id_associado=id_associado).update(responsavel=True)

        responsavel = ResponsavelFinanceiro.objects.filter(id_associado=id_associado).first()
        responsavel.id_responsavel = Associado.objects.filter(id_associado=id_responsavel).first()
        responsavel.save()

        return redirect(
            "editar-associado",
            id_associado=id_associado,
        )

@login_required(login_url="/v1/login/")
@permission_required('v1.view_associado', login_url="/v1/app/")
def vincularPlano(request, id_associado):
    if request.method == "GET":
        return render(
            request,
            "vincular-plano.html",
            {
                "id_associado": id_associado,
                "planos": Planos.objects.all()
            }
        )
    else:
        id_plano = request.POST.get("plano")
        plano = Planos.objects.filter(id_plano=id_plano, estado=True).first()
        if not plano:
            messages.error(request, "Plano não encontrado.")
            return redirect("vincular-plano", id_associado=id_associado)
        else:
            Associado.objects.filter(id_associado=id_associado).update(id_planos=plano.id_plano)
            return redirect("confirmar-cadastro", id_associado=id_associado)


@login_required(login_url="/v1/login/")
@permission_required('v1.view_associado', login_url="/v1/app/")
def confirmarCadastro(request, id_associado):
    associado = Associado.objects.get(id_associado=id_associado)
    responsavel_obj = ResponsavelFinanceiro.objects.filter(id_associado=associado).first()
    responsavel = responsavel_obj.id_responsavel if responsavel_obj else associado

    if request.method == "POST":
        if request.POST.get("acao") == "cancelar":
            associado.delete()
            return redirect("associados")
        return redirect("associados")

    for i in range(Planos.objects.get(id_plano=associado.id_planos.id_plano).meses_antecipados):
        Mensalidades.objects.create(
            id_associado = associado,
            data_pagamento = None,
            vencimento = datetime.datetime.today(),
            periodo_referencia = buiga_utils.calcular_periodo_referencia(associado.id_planos.regime_cobranca, i),
            id_planos = associado.id_planos,
            valor = associado.id_planos.valor,
            estado_pagamento = "Pendente"
        )

    return render(request, "confirmar-cadastro.html", {
        "associado": associado,
        "responsavel": responsavel,
        "plano": associado.id_planos,
    })

@login_required(login_url="/v1/login/")
@permission_required('v1.view_associado', login_url="/v1/app/")
def alterarPlano(request, id_associado):
    if request.method == "GET":
        return render(
            request, 
            "alterar-plano.html", 
            {
                "id_associado": id_associado,
                "planos": Planos.objects.filter(estado=True)
            }
        )
    else:
        id_plano=request.POST.get("plano")
        if id_plano:
            plano = Planos.objects.get(id_plano=id_plano)
        else:
            messages.error(request, "É obrigatório escolher um plano.")
            return redirect("alterar-plano", id_associado=id_associado)
        if not plano:
            messages.error(request, "Plano não encontrado.")
            return redirect("alterar-plano", id_associado=id_associado)
        else:
            ultima_referencia = Mensalidades.objects.filter(id_associado=id_associado)
            if ultima_referencia:
                ultima_referencia = ultima_referencia.order_by("periodo_referencia").last().periodo_referencia
            else:
                ultima_referencia = datetime.date.today()
            associado = Associado.objects.get(id_associado=id_associado)
            referencia = buiga_utils.proxima_referencia(ultima_referencia, associado.id_planos.regime_cobranca)

            Mensalidades.objects.create(
                id_associado=associado,
                data_pagamento=None,
                vencimento=referencia.replace(day=associado.dia_cobranca),
                periodo_referencia=referencia,
                id_planos=plano,
                valor=plano.valor,
                estado_pagamento="Pendente"
            )
            Associado.objects.filter(id_associado=id_associado).update(id_planos=plano.id_plano)
            return redirect("editar-associado", id_associado=id_associado)

"""
    vencimento = models.DateField()
    periodo_referencia = models.DateField()
"""


@login_required(login_url="/v1/login/")
@permission_required('v1.view_planos', login_url="/v1/app/")
def planos(request):
    planos_ativos = Planos.objects.filter(estado=True)
    planos_inativos = Planos.objects.filter(estado=False)
    return render(request, "planos.html", {"planos_ativos": planos_ativos, "planos_inativos": planos_inativos})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_planos', login_url="/v1/app/")
def filtroPlanos(request):
    if request.method == "POST":
        filtro = request.POST.get("busca")
        planos_ativos = Planos.objects.filter(nome_plano__icontains=filtro, estado=True)
        planos_inativos = Planos.objects.filter(nome_plano__icontains=filtro, estado=False)
        return render(request, "planos.html", {"planos_ativos": planos_ativos, "planos_inativos": planos_inativos})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_planos', login_url="/v1/app/")
def editarPlano(request, id_plano):
    plano = Planos.objects.get(id_plano=id_plano)
    if request.method == "POST":
        valor = request.POST.get("valor")
        nome_plano = request.POST.get("nome")
        aceita_dinheiro = request.POST.get("dinheiro")
        aceita_pix = request.POST.get("pix")
        regime_cobranca = request.POST.get("regime_cobranca")
        meses_antecipados = request.POST.get("meses_antecipados")
        
        if valor == "":
            valor = plano.valor
        if int(valor) < 0:
            messages.error(request, "O campo 'Valor' deve ser positivo.")
            return redirect("editar-plano", id_plano=id_plano)
        if not nome_plano:
            messages.error(request, "O campo 'Nome do plano' é obrigatório.")
            return redirect("editar-plano", id_plano=id_plano)
        if bool(re.search(r'[^\w\s]', nome_plano, re.UNICODE)):
            messages.error(request, "Nome inválido")
            return redirect("editar-plano", id_plano=id_plano)
        if not aceita_dinheiro:
            aceita_dinheiro = False
        if not aceita_pix:
            aceita_pix = False
        if aceita_dinheiro == False and aceita_pix == False:
            messages.error(request, "O plano deve aceitar pelo menos uma forma de pagamento.")
            return redirect("editar-plano", id_plano=id_plano)
        if not regime_cobranca:
            messages.error(request, "O campo 'Regime de cobrança' é obrigatório.")
            return redirect("editar-plano", id_plano=id_plano)
        if not meses_antecipados:
            messages.error(request, "O campo 'Meses antecipados' é obrigatório.")
            return redirect("editar-plano", id_plano=id_plano)
        if int(meses_antecipados) < 0:
            messages.error(request, "O campo 'Meses antecipados' deve ser positivo.")
            return redirect("editar-plano", id_plano=id_plano)

        plano.nome_plano = nome_plano
        plano.valor = valor
        plano.aceita_dinheiro = aceita_dinheiro
        plano.aceita_pix = aceita_pix
        plano.regime_cobranca = regime_cobranca
        plano.meses_antecipados = meses_antecipados
        plano.save()
        return redirect("planos")
    
    return render(request, "editar-plano.html", {"plano": plano})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_planos', login_url="/v1/app/")
def novoPlano(request):
    if request.method == "POST":
        nome_plano = request.POST.get("nome")
        valor = request.POST.get("valor")
        meses_antecipados = request.POST.get("meses_antecipados")
        aceita_dinheiro = request.POST.get("Dinheiro") == "True"
        aceita_pix = request.POST.get("Pix") == "True"
        regime_cobranca = request.POST.get("regime_cobranca")

        if bool(re.search(r'[^\w\s]', nome_plano, re.UNICODE)):
            messages.error(request, "Nome do plano inválido")
            return redirect("novo-plano")
        if not nome_plano:
            messages.error(request, "O campo 'Nome do plano' é obrigatório.")
            return redirect("novo-plano")
        if Planos.objects.filter(nome_plano=nome_plano).exists():
            messages.error(request, "Plano com mesmo nome já existe")
            return redirect("novo-plano")
        if not valor:
            messages.error(request, "O campo 'Valor' é obrigatório.")
            return redirect("novo-plano")
        if not meses_antecipados:
            messages.error(request, "O campo 'Meses antecipados' é obrigatório.")
            return redirect("novo-plano")
        if not aceita_dinheiro:
            aceita_dinheiro = False
        if not aceita_pix:
            aceita_pix = False
        if aceita_dinheiro == False and aceita_pix == False:
            messages.error(request, "O plano deve aceitar pelo menos uma forma de pagamento.")
            return redirect("novo-plano")
        if not regime_cobranca:
            messages.error(request, "O campo 'Regime de cobrança' é obrigatório.")
            return redirect("novo-plano")
        if int(meses_antecipados) < 0:
            messages.error(request, "O campo 'Meses antecipados' deve ser positivo.")
            return redirect("novo-plano")
        if int(valor) < 0:
            messages.error(request, "O campo 'Valor' deve ser positivo.")
            return redirect("novo-plano")

        Planos.objects.create(
            nome_plano=nome_plano,
            valor=valor,
            meses_antecipados=meses_antecipados if meses_antecipados else 1,
            aceita_dinheiro=aceita_dinheiro,
            aceita_pix=aceita_pix,
            regime_cobranca=regime_cobranca,
            estado=True
        ).save()
        return redirect("planos")
    return render(request, "novo-plano.html")

@login_required(login_url="/v1/login/")
@permission_required('v1.view_planos', login_url="/v1/app/")
def togglePlano(request, id_plano):
    plano = get_object_or_404(Planos, id_plano=id_plano)
    plano.estado = not plano.estado
    plano.save()
    return redirect("planos")

@login_required(login_url="/v1/login/")
@permission_required('v1.view_planos', login_url="/v1/app/")
def inativarPlano(request, id_plano):
    plano = get_object_or_404(Planos, id_plano=id_plano)
    if request.method == "POST":
        plano.estado = False
        plano.save()
        return redirect("planos")
    return render(request, "confirmar-inativacao-plano.html", {"plano": plano})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_planos', login_url="/v1/app/")
def reativarPlano(request, id_plano):
    plano = get_object_or_404(Planos, id_plano=id_plano)
    if request.method == "POST":
        plano.estado = True
        plano.save()
        return redirect("planos")
    return render(request, "confirmar-reativacao-plano.html", {"plano": plano})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_mensalidades', login_url="/v1/app/")
def cobrancas(request):
    cobrancas = Mensalidades.objects.all()

    totals = {"pagas": cobrancas.filter(estado_pagamento="Pago").aggregate(total=Count('id_mensalidade'), valor=Sum('valor')),
              "pendentes": cobrancas.filter(estado_pagamento="Pendente").aggregate(total=Count('id_mensalidade'), valor=Sum('valor')),
              "atrasadas": cobrancas.filter(estado_pagamento="Atrasado").aggregate(total=Count('id_mensalidade'), valor=Sum('valor'))
              }

    return render(request, "cobrancas.html", {"cobrancas": cobrancas, "totals": totals})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_mensalidades', login_url="/v1/app/")
def filtroCobrancas(request):
    if request.method == "POST":
        filtro = request.POST.get("busca")
        estado = request.POST.get("estado_pagamento")
        cobrancas = Mensalidades.objects.filter(id_associado__nome__icontains=filtro) | Mensalidades.objects.filter(id_associado__responsavelfinanceiro__id_responsavel__nome__icontains=filtro)
        if estado != "Todos":
            cobrancas = cobrancas.filter(estado_pagamento=estado)

        totals = {"pagas": cobrancas.filter(estado_pagamento="Pago").aggregate(total=Count('id_mensalidade'), valor=Sum('valor')),
                "pendentes": cobrancas.filter(estado_pagamento="Pendente").aggregate(total=Count('id_mensalidade'), valor=Sum('valor')),
                "atrasadas": cobrancas.filter(estado_pagamento="Atrasado").aggregate(total=Count('id_mensalidade'), valor=Sum('valor'))
                }

        return render(request, "cobrancas.html", {"cobrancas": cobrancas, "totals": totals}) 
    else:
        return redirect("cobrancas")

@login_required(login_url="/v1/login/")
@permission_required('v1.view_mensalidades', login_url="/v1/app/")
def confirmarPagamento(request, id_mensalidade):
    cobranca = Mensalidades.objects.get(id_mensalidade=id_mensalidade)
    if request.method == "POST":
        cobranca.data_pagamento = datetime.datetime.today()
        cobranca.estado_pagamento = "Pago"
        cobranca.save()
        return redirect("cobrancas")
    else:
        return render(request, "confirmar-pagamento.html", {"cobranca": cobranca})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_patrimonio', login_url="/v1/app/")
def patrimonio(request):
    patrimonios = Patrimonio.objects.annotate(manutencoes=Count("manutencao"))
    total_valor = sum(p.valor for p in patrimonios)
    manutencoes = Manutencao.objects.all()

    return render(request, "patrimonio.html", {"patrimonios": patrimonios, "manutencoes": manutencoes, "total_valor": total_valor})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_patrimonio', login_url="/v1/app/")
def patrimonioFiltro(request):
    if request.method == "POST":
        filtro = request.POST.get("busca")
        patrimonios = Patrimonio.objects.filter(nome_patrimonio__icontains=filtro)        
        patrimonios = patrimonios.annotate(manutencoes=Count("manutencao"))
        total_valor = sum(p.valor for p in patrimonios)
        manutencoes = Manutencao.objects.filter(id_patrimonio__in=patrimonios.values_list("id_patrimonio", flat=True))

    return render(request, "patrimonio.html", {"patrimonios": patrimonios, "manutencoes": manutencoes, "total_valor": total_valor})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_patrimonio', login_url="/v1/app/")
def novoBem(request):
    if request.method == "POST":
        nome_patrimonio = request.POST.get("nome")
        descricao = request.POST.get("descricao")
        valor = request.POST.get("valor")
        estado = request.POST.get("estado")
        data_aquisicao = request.POST.get("data")
        
        if bool(re.search(r'[^\w\s]', nome_patrimonio, re.UNICODE)):
            messages.error(request, "Nome do patrimonio inválido")
        if not nome_patrimonio or not descricao or not valor or not estado or not data_aquisicao:
            messages.error(request, "Todos os campos são obrigatórios")
            return redirect("novo-bem")
        if datetime.datetime.strptime(data_aquisicao, "%Y-%m-%d").date() > datetime.date.today():
            messages.error(request, "Data de aquisição não pode ser no futuro")
            return redirect("novo-bem")
        if float(valor) < 0:
            messages.error(request, "O campo 'Valor' deve ser positivo.")
            return redirect("novo-bem")

        bem = Patrimonio.objects.create(
            nome_patrimonio=nome_patrimonio,
            descricao=descricao, 
            valor=valor,
            estado=estado,
            data_aquisicao=data_aquisicao,
        )
        bem.save()
        return redirect("patrimonio")
    return render(request, "novo-bem.html")

@login_required(login_url="/v1/login/")
@permission_required('v1.view_patrimonio', login_url="/v1/app/")
def editarBem(request, id_patrimonio):
    patrimonio = get_object_or_404(Patrimonio, id_patrimonio=id_patrimonio)
    manutencoes = Manutencao.objects.filter(id_patrimonio=id_patrimonio)
    if request.method == "POST":
        patrimonio.nome_patrimonio = request.POST.get("nome_patrimonio")
        patrimonio.numero_serie = request.POST.get("numero_serie")
        patrimonio.descricao = request.POST.get("descricao")
        patrimonio.data_aquisicao = request.POST.get("data_aquisicao")
        patrimonio.valor_aquisicao = request.POST.get("valor_aquisicao")
        patrimonio.save()

        messages.success(request, "Bem atualizado com sucesso.")
        return redirect("patrimonio")
    return render(request, "editar-bem.html", {"patrimonio": patrimonio, "manutencoes": manutencoes})

@login_required(login_url="/v1/login/")
@user_passes_test(lambda u: u.is_staff, login_url="/v1/app/")
def confirmarBaixaBem(request, id_patrimonio):
    patrimonio = get_object_or_404(Patrimonio, id_patrimonio=id_patrimonio)
    return render(request, "confirmar-baixa-bem.html", {"patrimonio": patrimonio})

@login_required(login_url="/v1/login/")
@user_passes_test(lambda u: u.is_staff, login_url="/v1/app/")
def baixarBem(request, id_patrimonio):
    patrimonio = get_object_or_404(Patrimonio, id_patrimonio=id_patrimonio)
    if request.method == "POST":
        patrimonio.estado = "Baixado"
        patrimonio.save()
        messages.success(request, "Bem baixado com sucesso.")
        return redirect("patrimonio")
    return render(request, "confirmar-baixa-bem.html", {"patrimonio": patrimonio})


@login_required(login_url="/v1/login/")
@permission_required('v1.view_patrimonio', login_url="/v1/app/")
def registrarManutencao(request, id_patrimonio):
    patrimonio = get_object_or_404(Patrimonio, id_patrimonio=id_patrimonio)
    if request.method == "POST":
        descricao = request.POST.get("descricao")
        valor = request.POST.get("valor")
        data = request.POST.get("data")
        
        if not descricao or not valor or not data:
            messages.error(request, "Todos os campos são obrigatórios.")
            return redirect("editar-bem", id_patrimonio=id_patrimonio)
        if datetime.datetime.strptime(data, "%Y-%m-%d").date() > datetime.date.today():
            messages.error(request, "Data da manutenção não pode ser no futuro.")
            return redirect("editar-bem", id_patrimonio=id_patrimonio)
        if float(valor) < 0:
            messages.error(request, "O campo 'Valor' deve ser positivo.")
            return redirect("editar-bem", id_patrimonio=id_patrimonio)
        if datetime.datetime.strptime(data, "%Y-%m-%d").date() < patrimonio.data_aquisicao:
            messages.error(request, "Data da manutenção não pode ser anterior à data de aquisição do bem.")
            return redirect("editar-bem", id_patrimonio=id_patrimonio)
        
        manutencao = Manutencao.objects.create(
            id_patrimonio=patrimonio,
            descricao=descricao,
            valor=valor,
            data=data
        )
        manutencao.save()
        messages.success(request, "Manutenção registrada com sucesso.")
        return redirect("editar-bem", id_patrimonio=id_patrimonio)
    return render(request, "editar-bem.html", {"patrimonio": patrimonio})


@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def projetos(request):
    projetos = (
        Projeto.objects.all()
        .annotate(
            total_gasto=(Sum("movimentacaofinanceira__valor") or 0),
        )
        .order_by("-data_inicio")
    )
    for projeto in projetos:
        total = projeto.total_gasto or 0
        if projeto.valor > 0:
            projeto.percentual = (total / projeto.valor) * 100
        else:
            projeto.percentual = 0
    
    total_capitado = sum(p.valor for p in projetos)
    total_gasto = sum(m.valor for m in MovimentacaoFinanceira.objects.all())
    saldo_disponivel = total_capitado - total_gasto
    return render(request, "projetos.html", {"projetos": projetos, "total_capitado": total_capitado, "total_gasto": total_gasto, "saldo_disponivel": saldo_disponivel})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def projetosFiltro(request):
    if request.method == "POST":
        filtro = request.POST.get("busca")
        projetos = (
            (Projeto.objects.filter(nome_projeto__icontains=filtro) | Projeto.objects.filter(nome_doador__icontains=filtro))
            .annotate(
                total_gasto=(Sum("movimentacaofinanceira__valor") or 0),
            )
            .order_by("-data_inicio")
        )
        for projeto in projetos:
            total = projeto.total_gasto or 0
            if projeto.valor > 0:
                projeto.percentual = (total / projeto.valor) * 100
            else:
                projeto.percentual = 0
        total_capitado = sum(p.valor for p in projetos)
        total_gasto = sum(m.valor for m in MovimentacaoFinanceira.objects.filter(id_projeto__in=projetos.values_list("id_projeto", flat=True)))
        saldo_disponivel = total_capitado - total_gasto
        return render(request, "projetos.html", {"projetos": projetos, "total_capitado": total_capitado, "total_gasto": total_gasto, "saldo_disponivel": saldo_disponivel})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def novoProjeto(request):
    if request.method == "POST":
        nome_projeto = request.POST.get("nome")
        descricao = request.POST.get("descricao")
        valor_total = request.POST.get("valor_total")
        tipo_doador = request.POST.get("tipo_doador")
        nome_doador = request.POST.get("doador")
        responsavel = request.POST.get("responsavel")
        data_inicio = request.POST.get("data_inicio")
        data_fim = request.POST.get("data_fim")
        
        if not nome_projeto or not descricao or not valor_total or not tipo_doador or not nome_doador or not responsavel or not data_inicio or not data_fim:
            messages.error(request, "Todos os campos são obrigatórios.")
            return redirect("novo-projeto")
        if data_inicio > data_fim:
            messages.error(request, "A data de início não pode ser maior que a data de fim.")
            return redirect("novo-projeto")
        if float(valor_total) < 0:
            messages.error(request, "O valor total do projeto não pode ser negativo.")
            return redirect("novo-projeto")
        
        projeto = Projeto.objects.create(
            nome_projeto=nome_projeto,
            descricao=descricao,
            estado="Em andamento",
            valor=valor_total,
            tipo_doador=tipo_doador,
            nome_doador=nome_doador,
            responsavel=responsavel,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        projeto.save()
        return redirect("projetos")
    return render(request, "novo-projeto.html")

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def editarProjeto(request, id_projeto):
    projeto = get_object_or_404(Projeto, id_projeto=id_projeto)
    if request.method == "POST":
        projeto.nome_projeto = request.POST.get("nome")
        projeto.descricao = request.POST.get("descricao")
        projeto.valor = request.POST.get("valor_total")
        projeto.tipo_doador = request.POST.get("tipo_doador")
        projeto.nome_doador = request.POST.get("doador")
        projeto.responsavel = request.POST.get("responsavel")
        projeto.data_inicio = request.POST.get("data_inicio")
        projeto.data_fim = request.POST.get("data_fim")
        projeto.save()
        messages.success(request, "Projeto atualizado com sucesso.")
        return redirect("projetos")
    
    gasto_total = sum(m.valor for m in MovimentacaoFinanceira.objects.filter(id_projeto=projeto))
    disponibilidade = projeto.valor - gasto_total
    vinculos = VinculoAlunoProjeto.objects.filter(id_projeto=projeto)
    return render(request, "editar-projeto.html", {"projeto": projeto, "gastos": MovimentacaoFinanceira.objects.filter(id_projeto=projeto), "gasto_total": gasto_total, "disponibilidade": disponibilidade, "vinculos": vinculos})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def vincularAlunos(request, id_projeto):
    alunos = Alunos.objects.all()
    projeto = Projeto.objects.get(id_projeto=id_projeto)
    if request.method == "POST":
        # IDs dos alunos selecionados no formulário
        alunos_selecionados = request.POST.getlist("alunos")

        # Remove vínculos antigos
        VinculoAlunoProjeto.objects.filter(id_projeto=projeto).delete()

        # Cria novos vínculos
        for id_aluno in alunos_selecionados:
            aluno = Alunos.objects.get(id_aluno=id_aluno)
            VinculoAlunoProjeto.objects.create(id_projeto=projeto, id_aluno=aluno)

        return redirect("editar-projeto", id_projeto=projeto.id_projeto)

    alunos_selecionados = VinculoAlunoProjeto.objects.filter(id_projeto=projeto).values_list("id_aluno", flat=True)
    return render(request, "vincular-aluno.html", {"projeto": projeto, "alunos": alunos, "alunos_selecionados": alunos_selecionados})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def novoGasto(request, id_projeto):
    projeto = get_object_or_404(Projeto, id_projeto=id_projeto)
    if request.method == "POST":
        descricao = request.POST.get("descricao")
        categoria = request.POST.get("categoria")
        data = request.POST.get("data")
        valor = request.POST.get("valor")

        if not descricao or not categoria or not data or not valor:
            messages.error(request, "Todos os campos são obrigatórios.")
            return redirect("editar-projeto", id_projeto=id_projeto)
        
        gasto = MovimentacaoFinanceira.objects.create(
            id_projeto=projeto,
            descricao=descricao,
            categoria=categoria,
            data=data,
            valor=valor
        )
        gasto.save()
        messages.success(request, "Gasto vinculado ao projeto com sucesso.")
        return redirect("editar-projeto", id_projeto=id_projeto)
    return render(request, "editar-projeto.html", {"projeto": projeto})


@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def alunos(request):
    alunos = Alunos.objects.all()
    return render(request, "alunos.html", {"alunos": alunos})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def alunosFiltro(request):
    if request.method == "POST":
        filtro = request.POST.get("busca")
        alunos = Alunos.objects.filter(nome__icontains=filtro) | Alunos.objects.filter(cpf__icontains=filtro)
        return render(request, "alunos.html", {"alunos": alunos})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def novoAluno(request):
    if request.method == "POST":
        nome = request.POST.get("nome")
        nascimento = request.POST.get("nascimento")
        cpf = request.POST.get("cpf")
        escola = request.POST.get("escola")
        serie = request.POST.get("serie")
    
        if not nome:
            messages.error(request, "Nome é obrigatório.")
            return redirect("novo-aluno")
        if not buiga_utils.validar_data(nascimento):
            messages.error(request, "Data inválida")
            return redirect("novo-aluno")
        if not nascimento:
            messages.error(request, "Data de nascimento é obrigatória.")
            return redirect("novo-aluno")
        if cpf and Alunos.objects.filter(cpf=cpf).exists():
            messages.error(request, "CPF já cadastrado.")
            return redirect("novo-aluno")
        if not buiga_utils.cpf_valido(cpf):
            messages.error(request, "CPF inválido.")
            return redirect("novo-aluno")
        else:
            cpf = "".join(filter(str.isdigit, cpf))

        responsavel_legal = ResponsavelLegal.objects.filter(nome="Sem responsável legal").first()
        if not responsavel_legal:
            responsavel_legal = ResponsavelLegal.objects.create(
                nome="Sem responsável legal",
                cpf=0,
                telefone=0,
                email="responsavel@exemplo.com",
                endereco="Sem endereço"
            ).save()
        responsavel_legal = ResponsavelLegal.objects.filter(nome="Sem responsável legal").first()
        aluno = Alunos.objects.create(
            nome=nome,
            nascimento=nascimento,
            cpf=cpf,
            escola=escola,
            serie=serie,
            estado=True,
        )
        aluno.save()
        ResponsabilidadeLegal.objects.create(
            id_aluno=aluno,
            id_responsavel=responsavel_legal
        ).save()
        return redirect("vincular-responsavel-legal", id_aluno=aluno.id_aluno, id_responsavel_legal=0)
    return render(request, "novo-aluno.html")

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def vincularResponsavelLegal(request, id_aluno, id_responsavel_legal):
    aluno = Alunos.objects.filter(id_aluno=id_aluno).first()
    if request.method == "POST":
        responsavel_legal = ResponsavelLegal.objects.filter(id_responsavel=id_responsavel_legal).first()
        if responsavel_legal.nome == "Sem responsável legal":
            messages.error(request, "É necessário vincular um responsável legal")
            return redirect("vincular-responsavel-legal", id_aluno=id_aluno, id_responsavel_legal=id_responsavel_legal)

        relacionamento = ResponsabilidadeLegal.objects.get(id_aluno=aluno)
        relacionamento.id_responsavel = responsavel_legal
        relacionamento.save()
        return redirect("confirmar-aluno", id_aluno=id_aluno)#TODO

    if id_responsavel_legal == 0:
        responsavel_legal = ResponsavelLegal.objects.filter(nome="Sem responsável legal").first()
        return redirect("vincular-responsavel-legal", id_aluno=aluno.id_aluno, id_responsavel_legal=responsavel_legal.id_responsavel)

    responsavel_legal = ResponsavelLegal.objects.filter(id_responsavel=id_responsavel_legal).first()
    return render(request, "vincular-responsavel-legal.html", {"aluno": aluno, "responsavel_legal": responsavel_legal})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def confirmarAluno(request, id_aluno):
    if request.method == "POST":
        return redirect("alunos")
    aluno = Alunos.objects.get(id_aluno=id_aluno)
    responsavel_legal = ResponsabilidadeLegal.objects.filter(id_aluno=aluno).first().id_responsavel
    return render(request, "confirmar-aluno.html", {"aluno": aluno, "responsavel": responsavel_legal})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def buscarResponsavelLegal(request, id_aluno):
    responsavel_legal = ResponsavelLegal.objects.filter(cpf=request.POST.get("cpf")).first()
    if not responsavel_legal:
        messages.error(request, "CPF do Responsável Legal não encontrado.")
        return redirect("vincular-responsavel-legal", id_aluno=id_aluno, id_responsavel_legal=0)
    return redirect(
        "vincular-responsavel-legal",
        id_aluno=id_aluno,
        id_responsavel_legal=responsavel_legal.id_responsavel,
    )

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def editarAluno(request, id_aluno):
    return render(request, "editar-aluno.html", {"aluno": Alunos.objects.get(id_aluno=id_aluno)})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def alterarResponsavelLegal(request, id_aluno, id_responsavel_legal):
    aluno = Alunos.objects.get(id_aluno=id_aluno)
    responsavel_legal = ResponsavelLegal.objects.get(id_responsavel=id_responsavel_legal)
    if request.method == "GET":
        return render(request, "alterar-responsavel-legal.html", {"aluno": aluno, "responsavel_legal": responsavel_legal})
    elif request.method == "POST":
        relacionamento = ResponsabilidadeLegal.objects.get(id_aluno=aluno)
        relacionamento.id_responsavel = responsavel_legal
        relacionamento.save()
        return redirect("editar-aluno", id_aluno=aluno.id_aluno)

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def buscarAlterarResponsavelLegal(request, id_aluno):
    responsavel_legal = ResponsavelLegal.objects.filter(cpf=request.POST.get("cpf")).first()
    if not responsavel_legal:
        messages.error(request, "CPF do Responsável Legal não encontrado.")
        return redirect("vincular-responsavel-legal", id_aluno=id_aluno, id_responsavel_legal=0)
    return redirect(
        "alterar-responsavel-legal",
        id_aluno=id_aluno,
        id_responsavel_legal=responsavel_legal.id_responsavel,
    )

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def confirmarExclusaoAluno(request, id_aluno):
    aluno = get_object_or_404(Alunos, id_aluno=id_aluno)
    return render(request, "confirmar-exclusao-aluno.html", {"aluno": aluno})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def excluirAluno(request, id_aluno):
    Alunos.objects.get(id_aluno=id_aluno).delete()
    return redirect("alunos")

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def responsavelLegal(request):
    responsaveis = ResponsavelLegal.objects.all()
    return render(request, "responsavel-legal.html", {"responsaveis": responsaveis})

@login_required(login_url="/v1/login")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def responsavelLegalFiltro(request):
    if request.method == "POST":
        filtro = request.POST.get("busca")
        responsaveis = ResponsavelLegal.objects.filter(nome__icontains=filtro) | ResponsavelLegal.objects.filter(cpf__icontains=filtro)
        return render(request, "responsavel-legal.html", {"responsaveis": responsaveis})
    return render(request, "responsavel-legal.html")

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def novoResponsavelLegal(request):
    if request.method == "POST":
        nome = request.POST.get("nome")
        cpf = request.POST.get("cpf")
        telefone = request.POST.get("telefone")
        email = request.POST.get("email")
        endereco = request.POST.get("endereco")

        if not nome or not cpf or not telefone or not email or not endereco:
            messages.error(request, "Todos os campos são obrigatórios.")
            return redirect("novo-responsavel-legal")
        if not buiga_utils.cpf_valido(cpf):
            messages.error(request, "CPF inválido.")
            return redirect("novo-responsavel-legal")
        else:
            cpf = "".join(filter(str.isdigit, cpf))
        if len(telefone) != 11:
            messages.error(request, "Telefone precisa ter 11 dígitos.")
            return redirect("novo-responsavel-legal") 

        ResponsavelLegal.objects.create(
            nome=nome,
            cpf=cpf,
            telefone=telefone,
            email=email,
            endereco=endereco,
            estado=True
        ).save()
        return redirect("responsavel-legal")
    return render(request, "novo-responsavel-legal.html")

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def editarResponsavelLegal(request, id_responsavel_legal):
    return render(request, "editar-responsavel-legal.html", {"responsavel": ResponsavelLegal.objects.get(id_responsavel=id_responsavel_legal)})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def confirmarExclusaoResponsavelLegal(request, id_responsavel_legal):
    responsavel_legal = ResponsavelLegal.objects.get(id_responsavel=id_responsavel_legal)
    return render(request, "confirmar-exclusao-responsavel-legal.html", {"responsavel": responsavel_legal})

@login_required(login_url="/v1/login/")
@permission_required('v1.view_projeto', login_url="/v1/app/")
def excluirResponsavelLegal(request, id_responsavel_legal):
    responsavel_legal = ResponsavelLegal.objects.get(id_responsavel=id_responsavel_legal)
    if request.method == "POST":
        responsaveis = ResponsabilidadeLegal.objects.filter(id_responsavel=id_responsavel_legal).update(
            id_responsavel=ResponsavelLegal.objects.filter(nome="Sem responsável legal").first())
        responsavel_legal.delete()

        return redirect("responsavel-legal")

@login_required(login_url="/v1/login/")
def usuario(request):
    if request.method == "POST":
        user = request.user
        first_name = request.POST.get("first_name") #Nome completo
        email = request.POST.get("email")

        if not first_name or not email:
            messages.error(request, "Todos os campos são obrigatórios")
            return render(request, "usuario.html", {"user": request.user})

        if re.search(r"[!@#$%^&*(),.?\":{}|<>]", first_name):
            messages.error(request, "Não pode conter caracteres especiais no nome do usuário")
            return render(request, "usuario.html", {"user": request.user})

        user.first_name = first_name
        user.email = email

        user.save()
        messages.success(request, "Dados atualizados com sucesso.")
        return redirect("usuario")
    return render(request, "usuario.html", {"user": request.user})

@login_required(login_url="/v1/login/")
def alterarSenha(request):
    if request.method == "POST":
        user = request.user
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not user.check_password(current_password):
            messages.error(request, "Senha atual incorreta.")
            return redirect("usuario")
        validacao = buiga_utils.validar_senha(new_password, confirm_password)
        if validacao is True:
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Senha alterada com sucesso.")
        else:
            messages.error(request, validacao)
            return redirect("usuario")
        return redirect("usuario")
    
@login_required(login_url="/v1/login/")
@user_passes_test(lambda u: u.is_staff, login_url="/v1/app/")
def administracao(request):
    usuarios = []
    for usuario in User.objects.all().prefetch_related('user_permissions'):
        # Busca todas as permissões (individuais e de grupos) do usuário
        acesso = usuario.get_all_permissions()
        
        usuarios.append({
            'perfil': usuario,
            'acessos': acesso
        })
    return render(request, "administracao.html", {"usuarios": usuarios})

@login_required(login_url="/v1/login/")
@user_passes_test(lambda u: u.is_staff, login_url="/v1/app/")
def editarUsuario(request, id_usuario):
    if request.user.id == id_usuario:
        messages.error(request, "Não é possível editar próprio usuário por esse canal")
        return redirect("administracao")
    
    usuario = User.objects.get(id=id_usuario)
    if request.method == "POST":
        first_name = request.POST.get("nome")
        last_name = request.POST.get("funcao")
        email = request.POST.get("email")
        nova_senha = request.POST.get("senha")
        confirm_senha = request.POST.get("confirm_senha")
        acessos = [request.POST.get("associados"),
                   request.POST.get("planos"), 
                   request.POST.get("mensalidades"), 
                   request.POST.get("patrimonio"), 
                   request.POST.get("projetos"),
                   request.POST.get("whatsapp")
        ]

        if nova_senha != "" and confirm_senha != "":
            senha_validada = buiga_utils.validar_senha(nova_senha, confirm_senha) 
            if senha_validada is True:
                usuario.set_password(nova_senha)
            else:
                messages.error(request, senha_validada)
                return render(request, "editar-usuario.html", {"usuario":  usuario, "acessos": usuario.get_all_permissions()})
        if not first_name or not last_name or not email:
            messages.error(request, "Todos os campos são obrigatórios")
            return render(request, "editar-usuario.html", {"usuario":  usuario, "acessos": usuario.get_all_permissions()})
        if re.search(r"[!@#$%^&*(),.?\":{}|<>]", first_name):
            messages.error(request, "Não pode conter caracteres especiais no nome do usuário")
            return render(request, "editar-usuario.html", {"usuario":  usuario, "acessos": usuario.get_all_permissions()})
        if re.search(r"[!@#$%^&*(),.?\":{}|<>]", last_name):
            messages.error(request, "Não pode conter caracteres especiais na função da ONG do usuário")
            return render(request, "editar-usuario.html", {"usuario":  usuario, "acessos": usuario.get_all_permissions()})
        
        usuario.user_permissions.clear()
        for acesso in acessos:
            if acesso != None:
                usuario.user_permissions.add(Permission.objects.get(codename=acesso))

        usuario.is_staff = request.POST.get("administracao") == "True"

        usuario.first_name = first_name
        usuario.last_name = last_name
        usuario.email = email
        usuario.save()

        messages.success(request, "Usuário atualizado com sucesso.")
        return redirect("administracao")
    return render(request, "editar-usuario.html", {"usuario":  usuario, "acessos": usuario.get_all_permissions()})

@login_required(login_url="/v1/login/")
@user_passes_test(lambda u: u.is_staff, login_url="/v1/app/")
def novoUsuario(request):
    if request.method == "POST":
        username = request.POST.get("username")
        first_name = request.POST.get("nome")
        last_name = request.POST.get("funcao")
        email = request.POST.get("email")
        nova_senha = request.POST.get("senha")
        selected_permissions = [request.POST.get(nome) for nome in (
            "associados", "planos", "mensalidades", "patrimonio", "projetos", "whatsapp", "administracao"
        ) if request.POST.get(nome)]
        form_data = {
            "username": username or "",
            "nome": first_name or "",
            "email": email or "",
            "funcao": last_name or "",
        }

        usuarios = []
        for usuario_cadastrado in User.objects.all().prefetch_related("user_permissions"):
            usuarios.append({
                "perfil": usuario_cadastrado,
                "acessos": usuario_cadastrado.get_all_permissions(),
            })

        def erro_formulario(mensagem):
            messages.error(request, mensagem)
            return render(request, "administracao.html", {
                "usuarios": usuarios,
                "form_data": form_data,
                "selected_permissions": selected_permissions,
            })

        if User.objects.filter(username=username).exists():
            return erro_formulario("Nome de usuário já existe")
        if not username or not first_name or not last_name or not email or not nova_senha:
            return erro_formulario("Todos os campos são obrigatórios")
        if re.search(r"[!@#$%^&*(),.?\":{}|<>]", username):
            return erro_formulario("Não pode conter caracteres especiais no Usuário")
        if re.search(r"[!@#$%^&*(),.?\":{}|<>]", first_name):
            return erro_formulario("Não pode conter caracteres especiais no nome do usuário")
        if re.search(r"[!@#$%^&*(),.?\":{}|<>]", last_name):
            return erro_formulario("Não pode conter caracteres especiais na função da ONG")
        
        senha_validada = buiga_utils.validar_senha(nova_senha, nova_senha) 
        if senha_validada is True:
            pass
        else:
            return erro_formulario(senha_validada)

        usuario = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=nova_senha
        )
        for acesso in selected_permissions:
            if acesso == "True":
                continue
            app_label = "whatsapp" if acesso == "view_configuracaowhatsapp" else "v1"
            permissao = Permission.objects.filter(app_label=app_label, codename=acesso).first()
            if permissao:
                usuario.user_permissions.add(permissao)

        usuario.is_staff = request.POST.get("administracao") == "True"

        usuario.save()
        messages.success(request, "Usuário criado com sucesso.")
        return redirect("administracao")

@login_required(login_url="/v1/login/")
@user_passes_test(lambda u: u.is_staff, login_url="/v1/app/")
def excluirUsuario(request, id_user):
    usuario = User.objects.get(id=id_user)
    if request.method == "POST":
        usuario.delete()
        messages.success(request, "Usuário excluído com sucesso.")
        return redirect("administracao")
    return render(request, "confirmar-exclusao-usuario.html", {"usuario": usuario})
