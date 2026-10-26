from django.urls import path

from . import views

urlpatterns = [
    path("", views.loginPanel, name="index"),
    path("app/", views.app, name="app"),

    #Acesso
    path("login/", views.loginPanel, name="login"),
    path("logout/", views.logoutPanel, name="logout"),
    path("usuario/", views.usuario, name="usuario"),
    path("usuario/alterar-senha/", views.alterarSenha, name="alterar-senha"),

    #Dashboard
    path("dashboard/", views.dashboardPanel, name="dashboard"),

    #Associados
    path("associados/", views.associados, name="associados"),
    path("associados/filtro/", views.filtroAssociados, name="associados-filtro"),
    path("associado/novo/", views.novoAssociado, name="novo-associado"),
    path("associado/<int:id_associado>/responsavel/<int:id_responsavel>", views.vincularResponsavelFinanceiro, name="vincular-responsavel"),
    path("associado/<int:id_associado>/responsavel/<int:id_responsavel>/edicao", views.editarResponsavelFinanceiro, name="vincular-responsavel-edicao"),
    path("associado/busca/<int:id_associado>", views.buscarResponsavelPanel, name="buscar-responsavel"),
    path("associado/busca/<int:id_associado>/edicao", views.buscarEdicaoResponsavelPanel, name="buscar-responsavel-edicao"),
    path("associado/editar/<int:id_associado>", views.editarAssociadoPanel, name="editar-associado"),
    path("associado/editar/<int:id_associado>/responsavel/<int:id_responsavel>", views.editarResponsavelFinanceiro, name="editar-responsavel-financeiro"),
    path("associado/editar/<int:id_associado>/plano/", views.alterarPlano, name="alterar-plano"),
    path("associado/excluir/<int:id_associado>", views.excluirAssociado, name="excluir-associado"),
    path("associado/inativar/<int:id_associado>", views.inativarAssociado, name="inativar-associado"),
    path("associado/reativar/<int:id_associado>", views.reativarAssociado, name="reativar-associado"),
    path("associado/confirmar-inativacao/<int:id_associado>", views.confirmarInativacao, name="confirmar-inativacao"),
    path("associado/confirmar-reativacao/<int:id_associado>", views.confirmarReativacao, name="confirmar-reativacao"),
    path("associado/<int:id_associado>/vincular-plano", views.vincularPlano, name="vincular-plano"),
    path("associado/<int:id_associado>/confirmar", views.confirmarCadastro, name="confirmar-cadastro"),

    #Planos
    path("planos/", views.planos, name="planos"),
    path("planos/filtro/", views.filtroPlanos, name="planos-filtro"),
    path("plano/novo/", views.novoPlano, name="novo-plano"),
    path("plano/editar/<int:id_plano>/", views.editarPlano, name="editar-plano"),
    path("plano/toggle/<int:id_plano>/", views.togglePlano, name="toggle-plano"),
    path("plano/inativar-plano/<int:id_plano>/", views.inativarPlano, name="confirmar-inativacao-plano"),
    path("plano/reativar-plano/<int:id_plano>/", views.reativarPlano, name="confirmar-reativacao-plano"),

    #Cobranças
    path("cobrancas/", views.cobrancas, name="cobrancas"),
    path("cobrancas/filtro", views.filtroCobrancas, name="cobrancas-filtro"),
    path("cobrancas/<int:id_mensalidade>/confirmar-pagamento/", views.confirmarPagamento, name="confirmar-pagamento"),

    #Patrimonio
    path("patrimonio/", views.patrimonio, name="patrimonio"),
    path("patrimonio/filtro/", views.patrimonioFiltro, name="patrimonio-filtro"),
    path("patrimonio/novo/", views.novoBem, name="novo-bem"),
    path("patrimonio/confirmar-baixa/<int:id_patrimonio>/", views.confirmarBaixaBem, name="confirmar-baixa-bem"),
    path("patrimonio/baixa/<int:id_patrimonio>/", views.baixarBem, name="baixar-bem"),
    path("patrimonio/editar/<int:id_patrimonio>/", views.editarBem, name="editar-bem"),
    path("patrimonio/editar/<int:id_patrimonio>/manutencao", views.registrarManutencao, name="registrar_manutencao"),

    #Projetos
    path("projetos/", views.projetos, name="projetos"),
    path("projetos/filtro/", views.projetosFiltro, name="projetos-filtro"),
    path("projetos/novo/", views.novoProjeto, name="novo-projeto"),
    path("projetos/editar/<int:id_projeto>/", views.editarProjeto, name="editar-projeto"),
    path("projetos/editar/<int:id_projeto>/gasto/novo/", views.novoGasto, name="novo-gasto"),
    path("projetos/editar/<int:id_projeto>/vincular-aluno/", views.vincularAlunos, name="vincular-alunos"),

    #Alunos
    path("alunos/", views.alunos, name="alunos"),
    path("alunos/filtro/", views.alunosFiltro, name="alunos-filtro"),
    path("alunos/novo/", views.novoAluno, name="novo-aluno"),
    path("alunos/novo/<int:id_aluno>/responsavel-legal/<int:id_responsavel_legal>", views.vincularResponsavelLegal, name="vincular-responsavel-legal"),
    path("alunos/<int:id_aluno>/responsavel-legal/<int:id_responsavel_legal>", views.alterarResponsavelLegal, name="alterar-responsavel-legal"),
    path("alunos/<int:id_aluno>/responsavel-legal/", views.buscarAlterarResponsavelLegal, name="busca-alterar-responsavel-legal"),
    path("alunos/busca/<int:id_aluno>", views.buscarResponsavelLegal, name="buscar-responsavel-legal"),
    path("alunos/<int:id_aluno>/confirmar", views.confirmarAluno, name="confirmar-aluno"),
    path("alunos/editar/<int:id_aluno>/", views.editarAluno, name="editar-aluno"),
    path("alunos/confirmar-exclusao/<int:id_aluno>/", views.confirmarExclusaoAluno, name="confirmar-exclusao-aluno"),
    path("alunos/excluir/<int:id_aluno>/", views.excluirAluno, name="excluir-aluno"),

    #Responsável Legal
    path("responsavel-legal/", views.responsavelLegal, name="responsavel-legal"),
    path("responsavel-legal/filtro/", views.responsavelLegalFiltro, name="responsavel-legal-filtro"),
    path("responsavel-legal/novo/", views.novoResponsavelLegal, name="novo-responsavel-legal"),
    path("responsavel-legal/editar/<int:id_responsavel_legal>/", views.editarResponsavelLegal, name="editar-responsavel-legal"),
    path("responsavel-legal/confirmar-exclusao/<int:id_responsavel_legal>/", views.confirmarExclusaoResponsavelLegal, name="confirmar-exclusao-responsavel-legal"),
    path("responsavel-legal/excluir/<int:id_responsavel_legal>/", views.excluirResponsavelLegal, name="excluir-responsavel-legal"),

    #Administração de acesso
    path("administracao/", views.administracao, name="administracao"),
    path("administracao/editar/<int:id_usuario>", views.editarUsuario, name="editar-usuario"),
    path("administracao/novo/", views.novoUsuario, name="novo-usuario"),
    path("administracao/confirmar-exclusao/<int:id_user>", views.excluirUsuario, name="excluir-usuario"),
]
