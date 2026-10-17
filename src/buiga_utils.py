import re
import v1.models as models
import datetime
from dateutil.relativedelta import relativedelta
from django.utils import timezone

def cpf_valido(cpf) -> bool:
    # Validação de dados
    cpf = "".join(filter(str.isdigit, cpf))

    if len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False

    soma = 0
    for i in range(9):
        soma += int(cpf[i]) * (10 - i)

    digito1 = (soma * 10) % 11
    if digito1 == 10:
        digito1 = 0

    if digito1 != int(cpf[9]):
        return False

    soma = 0
    for i in range(10):
        soma += int(cpf[i]) * (11 - i)

    digito2 = (soma * 10) % 11
    if digito2 == 10:
        digito2 = 0

    if digito2 != int(cpf[10]):
        return False

    return True


def validar_senha(nova_senha: str, confirm_senha:str):
    """
    Valida se a senha é forte.
    Critérios:
    - Mínimo de 8 caracteres
    - Pelo menos uma letra maiúscula
    - Pelo menos uma letra minúscula
    - Pelo menos um dígito
    - Pelo menos um caractere especial (!@#$%^&*()-_=+ etc.)
    """
    if(nova_senha != confirm_senha):
        return "Senhas não conferem"
    if len(nova_senha) < 8:
        return "Senha deve conter no mínimo 8 caracteres."
    if not re.search(r"[A-Z]", nova_senha):
        return "Senha deve conter pelo menos uma letra maiúscula"
    if not re.search(r"[a-z]", nova_senha):
        return "Senha deve conter pelo menos uma letra minúscula"
    if not re.search(r"[0-9]", nova_senha):
        return "Senha deve conter pelo menos um dígito"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", nova_senha):
        return "Senha deve conter pelo menos um caractere especial"
    return True

def validar_data(date_str):
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False

def calcular_periodo_referencia(regime: str, frequencia: int) -> datetime.date:
    regime_cobranca = {
        "mensal": 1,
        "trimestral": 3,
        "semestral": 6,
        "anual": 12
    }
    return datetime.date.today().replace(day=1) + relativedelta(months=frequencia*regime_cobranca.get(regime, 1))

def verificar_cobrança_aberta(associado: models.Associado):
    cobrancas = models.Mensalidades.objects.filter(id_associado=associado.id_associado)
    cobrancas = cobrancas.exclude(estado_pagamento="Cancelado")
    cobrancas = cobrancas.exclude(estado_pagamento="Pago")
    return cobrancas.exists()

def proxima_referencia(ultima_referencia: datetime.date, regime: str) -> datetime.date:
    regime_cobranca = {
        "mensal": 1,
        "trimestral": 3,
        "semestral": 6,
        "anual": 12
    }
    return ultima_referencia + relativedelta(months=regime_cobranca.get(regime, 1))

def gerar_nova_cobranca(associado: models.Associado):
    if not verificar_cobrança_aberta(associado=associado):
        ultima_referencia = models.Mensalidades.objects.filter(id_associado=associado).order_by("periodo_referencia").last().periodo_referencia
        referencia = proxima_referencia(ultima_referencia, associado.id_planos.regime_cobranca)

        models.Mensalidades.objects.create(
            id_associado=associado,
            data_pagamento=None,
            vencimento=referencia.replace(day=associado.dia_cobranca),
            periodo_referencia=referencia,
            id_planos=associado.id_planos,
            valor=associado.id_planos.valor,
            estado_pagamento="Pendente"
        )

def gerar_cobranças():
    print(datetime.datetime.now().strftime("[%d/%b/%Y %H:%M:%S]") + " Gerados novas cobranças")
    for associado in models.Associado.objects.filter(estado="Ativo"):
        gerar_nova_cobranca(associado=associado)

def verificar_cobrancas_atrasadas():
    print(datetime.datetime.now().strftime("[%d/%b/%Y %H:%M:%S]") + " verificando cobranças atrasadas")
    for cobranca in models.Mensalidades.objects.filter(estado_pagamento="Pendente"):
        if cobranca.vencimento < datetime.date.today():
            cobranca.estado_pagamento = "Atrasado"
            cobranca.save()

def criar_cobranca_teste():
    associado = models.Associado.objects.get(id_associado = 1)
    models.Mensalidades.objects.create(
        id_associado = associado,
        data_pagamento = None,
        vencimento = datetime.datetime(2026, 7, 27, 0, 0), #Ano, Mês, Dia, Hora, Minuto
        periodo_referencia = datetime.datetime(2026, 6, 1, 0, 0), #Ano, Mês, Dia, Hora, Minuto || Sempre dia 1 do mês
        id_planos = associado.id_planos,
        valor = associado.id_planos.valor,
        estado_pagamento = "Pago"
    ).save()
