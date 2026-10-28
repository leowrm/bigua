# Biguá — Gestão de associados

Sistema web da Associação de Canoagem e Preservação Ambiental Biguá para gerenciar associados, planos, mensalidades, patrimônio, projetos, alunos e responsáveis, com integração ao WhatsApp Cloud API.

## Estado atual

O sistema possui área administrativa autenticada, controle de permissões, cadastros dos principais módulos, controle de mensalidades e integração de teste com o WhatsApp.

A automação de cobranças pelo WhatsApp está preparada, mas deve ser validada com o número oficial, templates aprovados e a conta da Meta antes de ser ativada em produção.

## Tecnologias

- Python 3.13 e Django 5.2
- Templates Django, HTML, CSS e JavaScript
- SQLite no desenvolvimento local
- PostgreSQL recomendado em produção
- WhatsApp Cloud API da Meta
- Gunicorn, Nginx e Let's Encrypt em produção
- GitHub Actions para CI

As dependências estão em [`src/requirements.txt`](src/requirements.txt). Node.js não é necessário para executar a aplicação atual.

## Estrutura

```text
bigua/
├── src/
│   ├── manage.py
│   ├── .env.example
│   ├── buiga_utils.py
│   ├── webapi/              # settings, URLs, WSGI e health check
│   ├── v1/                  # aplicação principal e telas administrativas
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── templates/
│   │   └── static/
│   └── whatsapp/            # webhook, menu, templates e disparos
├── deploy/                  # systemd, cron, Nginx e backup
├── public/
├── .github/workflows/       # CI do Django
├── AGENTS.md
└── README.md
```

## Executar localmente no Windows

Pré-requisitos: Python e Git.

```powershell
cd caminho\para\bigua\src
Copy-Item .env.example .env
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

Acesse `http://127.0.0.1:8000/` para a landing page, `http://127.0.0.1:8000/v1/` para o sistema, `http://127.0.0.1:8000/admin/` para o Django Admin e `http://127.0.0.1:8000/health/` para o health check.

### Ambiente virtual opcional

```powershell
cd caminho\para\bigua\src
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

O projeto também funciona sem `venv`. Para sair do ambiente virtual, execute `deactivate`.

### Banco local

O SQLite local fica em `src/mydatabase`. O arquivo é ignorado pelo Git; um clone novo começa com o banco vazio. O `.env` também é local e deve ser criado a partir de `src/.env.example`.

## Funcionalidades

### Acesso e permissões

- Login, logout e alteração de senha.
- Dashboard protegido.
- Administração de usuários.
- Permissões separadas para associados, planos, cobranças, patrimônio, projetos, administração e WhatsApp.
- Usuários `staff` têm acesso administrativo; usuários comuns recebem somente as seções autorizadas.
- Formulários preservam dados preenchidos quando há erro e destacam todos os campos inválidos.

### Associados, planos e cobranças

- Listagem, filtros, cadastro e edição de associados.
- Inativação, reativação e exclusão de associados.
- Validação de CPF, telefone, e-mail, nascimento e dia de cobrança.
- Responsável financeiro e vínculo de plano.
- Cadastro, edição, ativação e inativação de planos.
- Listagem e filtros de mensalidades.
- Confirmação manual de pagamento.
- Geração de mensalidades e atualização de cobranças por utilitários do projeto.

### Alunos e responsáveis legais

- Cadastro, edição e exclusão de alunos.
- Cadastro, edição e exclusão de responsáveis legais.
- Vínculo e alteração do responsável legal.
- Validação de CPF, telefone, e-mail e datas.

### Patrimônio e projetos

- Cadastro, edição, filtros e baixa de patrimônio.
- Registro de manutenções.
- Cadastro, edição e filtros de projetos.
- Registro de gastos.
- Vínculo de alunos aos projetos.

### Landing page

A rota `/` exibe a página pública da ONG com informações institucionais, galeria de imagens, formas de apoio, chave Pix, endereço e contato.

## WhatsApp

O módulo usa a WhatsApp Cloud API da Meta e possui webhook, menu numérico, consulta de mensalidades pendentes e atrasadas, resposta com chave Pix, encaminhamento para atendimento humano, registro de mensagens e estados, configuração de avisos, histórico de disparos, sincronização e edição de templates e comandos de teste.

A preparação de disparos cobre pré-vencimento, vencimento e atraso, mas deve ser validada em ambiente controlado antes de ativar a rotina no número oficial.

### Variáveis

```env
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_WABA_ID=
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_API_VERSION=v23.0
```

O `WHATSAPP_VERIFY_TOKEN` deve ser igual ao token cadastrado no webhook da Meta. Mensagens iniciadas pela ONG devem usar templates aprovados pela Meta; texto livre depende da janela de atendimento.

### Rotas principais

```text
/whatsapp/webhook/
/whatsapp/painel/configuracao/
/whatsapp/painel/historico/
/whatsapp/painel/templates/
/whatsapp/teste/
/whatsapp/scheduler/
```

### Comandos

Execute dentro de `src`:

```powershell
python manage.py gerar_disparos_whatsapp
python manage.py enviar_disparos_whatsapp
python manage.py enviar_teste_whatsapp --telefone 5551999999999 --template
python manage.py enviar_teste_whatsapp --telefone 5551999999999 --template-cobranca
```

O comando de teste também aceita `--mensagem` e `--parametros`, separados por ponto e vírgula.

## Testes e CI

```powershell
cd src
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test --verbosity 2
```

O workflow `.github/workflows/ci.yml` instala dependências, verifica sintaxe e configuração de produção, verifica e aplica migrações, coleta estáticos e executa os testes Django.

## Produção

A configuração atual usa VPS Hostinger, Ubuntu 24.04, PostgreSQL, Gunicorn, Nginx, HTTPS via Let's Encrypt, serviço systemd `bigua.service` e jobs periódicos via cron.

Arquivos em `deploy/`: `bigua.service`, `bigua-nginx.conf`, `bigua-cron` e `backup-postgres.sh`.

O ambiente de produção não deve usar o `.env.example`. Configure as variáveis secretas diretamente no servidor.

Após atualizar o código no VPS:

```bash
cd /opt/bigua/src
sudo -u bigua /opt/bigua/.venv/bin/python manage.py migrate
sudo -u bigua /opt/bigua/.venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart bigua
sudo systemctl status bigua --no-pager
```

## Migrações

Após alterar um model Django:

```powershell
cd src
python manage.py makemigrations
python manage.py migrate
python manage.py test
```

Os arquivos de migração devem ser versionados. O banco local, `.env`, tokens e senhas nunca devem ser commitados.

## Licença e uso

Projeto desenvolvido para a Associação de Canoagem e Preservação Ambiental Biguá. O código e os dados devem ser tratados conforme a autorização da ONG e as regras aplicáveis de proteção de dados.
