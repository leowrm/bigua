from django.db import models

# Create your models here.

class Associado(models.Model):
    id_associado = models.AutoField(primary_key=True)
    responsavel = models.BooleanField(default=True)
    nome = models.CharField(max_length=64)
    cpf = models.CharField(max_length=11)
    nascimento = models.DateField()
    email = models.EmailField(max_length=100)
    telefone = models.CharField(max_length=15)
    dia_cobranca = models.IntegerField()
    estado = models.CharField(max_length=20) #Ativo, Inativo
    id_planos = models.ForeignKey('Planos', on_delete=models.CASCADE)
    data_criacao = models.DateTimeField(auto_now_add=True)

class ResponsavelFinanceiro(models.Model):
    id_associado = models.OneToOneField(Associado, on_delete=models.CASCADE, primary_key=True)
    id_responsavel = models.ForeignKey(Associado, on_delete=models.CASCADE, related_name="responsavel_financeiro")

class Planos(models.Model):
    id_plano = models.AutoField(primary_key=True)
    nome_plano = models.CharField(max_length=64)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    meses_antecipados = models.IntegerField(default=0)
    aceita_dinheiro = models.BooleanField(default=True)
    aceita_pix = models.BooleanField(default=True)
    regime_cobranca = models.CharField(max_length=20) #mensal, trimestral, semestral, anual
    estado = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_plano

class Mensalidades(models.Model):
    id_mensalidade = models.AutoField(primary_key=True)
    id_associado = models.ForeignKey(Associado, on_delete=models.CASCADE)
    data_pagamento = models.DateField(null=True, blank=True)
    vencimento = models.DateField()
    periodo_referencia = models.DateField()
    id_planos = models.ForeignKey(Planos, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    estado_pagamento = models.CharField(max_length=20) #Pago/Pendente/Atrasado/Cancelado

class Endereco(models.Model):
    id_endereco = models.AutoField(primary_key=True)
    id_associado = models.ForeignKey(Associado, on_delete=models.CASCADE)
    rua = models.CharField(max_length=64)
    numero = models.CharField(max_length=10)
    complemento = models.CharField(max_length=50, null=True, blank=True)
    bairro = models.CharField(max_length=50)
    cidade = models.CharField(max_length=50)
    estado = models.CharField(max_length=20)
    cep = models.CharField(max_length=10)

class Alunos(models.Model):
    id_aluno = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=64)
    cpf = models.CharField(max_length=11)
    nascimento = models.DateField()
    escola = models.CharField(max_length=64)
    serie = models.CharField(max_length=40)
    estado = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

class ResponsavelLegal(models.Model):
    id_responsavel = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=64)
    cpf = models.CharField(max_length=11)
    telefone = models.CharField(max_length=15)
    email = models.EmailField(max_length=100)
    endereco = models.CharField(max_length=256)
    estado = models.CharField(max_length=20)
    data_criacao = models.DateTimeField(auto_now_add=True)

class ResponsabilidadeLegal(models.Model):
    id_aluno = models.OneToOneField(Alunos, on_delete=models.CASCADE, primary_key=True)
    id_responsavel = models.ForeignKey(ResponsavelLegal, on_delete=models.CASCADE, related_name="responsavel_legal")

class Projeto(models.Model):
    id_projeto = models.AutoField(primary_key=True)
    nome_projeto = models.CharField(max_length=64)
    descricao = models.TextField()
    estado = models.CharField(max_length=20)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    tipo_doador = models.CharField(max_length=20)
    nome_doador = models.CharField(max_length=64)
    responsavel = models.CharField(max_length=64)
    data_inicio = models.DateField()
    data_fim = models.DateField()

class MovimentacaoFinanceira(models.Model):
    id_movimentacao = models.AutoField(primary_key=True)
    id_projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.CharField(max_length=20)
    data = models.DateField()
    descricao = models.TextField()
    
class VinculoAlunoProjeto(models.Model):
    id_projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE)
    id_aluno = models.ForeignKey(Alunos, on_delete=models.CASCADE)

class Patrimonio(models.Model):
    id_patrimonio = models.AutoField(primary_key=True)
    nome_patrimonio = models.CharField(max_length=64)
    descricao = models.TextField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20)
    data_aquisicao = models.DateField()
    data_criacao = models.DateTimeField(auto_now_add=True)

class Manutencao(models.Model):
    id_manutencao = models.AutoField(primary_key=True)
    id_patrimonio = models.ForeignKey(Patrimonio, related_name="manutencao", on_delete=models.CASCADE)
    descricao = models.TextField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField()