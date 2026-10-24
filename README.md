**Unisinos São Leopoldo**

# Brisa-Biguá
Sistema web de gestão de associados e cobranças de mensalidades para a associação BIGUÁ, com automação via WhatsApp (em desenvolvimento).

## Stack
- **Backend:** Python 3 + Django
- **Banco de dados:** SQLite
- **Frontend:** Django Templates + CSS customizado (dark theme)

## Como executar

**Manual:**
```bash
cd src
copy .env.example .env   # Windows; no Linux/macOS: cp .env.example .env
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Acesse em `http://127.0.0.1:8000/v1/`

## Funcionalidades implementadas

| Módulo | Rota | Status |
|---|---|---|
| Login / Logout | `/v1/login/` | Implementado |
| Cadastro de usuário | `/v1/cadastro/` | Implementado |
| Dashboard | `/v1/dashboard/` | Implementado |
| Listagem de associados | `/v1/associados/` | Implementado |
| Cadastro de associado | `/v1/associado/novo/` | Implementado |
| Edição de associado | `/v1/associado/editar/<id>` | Implementado |
| Exclusão de associado | `/v1/associado/confirmar-exclusao/<id>` | Implementado |
| Responsável financeiro | `/v1/associado/<id>/responsavel/<id>` | Implementado |
| Vínculo de plano | `/v1/associado/<id>/vincular-plano` | Implementado |
| Confirmação de cadastro | `/v1/associado/<id>/confirmar` | Implementado |
| Planos | `/v1/planos/` | Interface sem lógica |
| Cobranças | `/v1/cobrancas/` | Interface (sem lógica) |

## Trabalho futuro

Os módulos abaixo têm templates criados e rotas reservadas, mas ainda sem implementação de views ou lógica:

- **Relatórios** — `/v1/relatorios/`
- **Projetos** — `/v1/projetos/`
- **Alunos** — `/v1/alunos/`
- **Patrimônio** — `/v1/patrimonio/`
- **Configurações** — `/v1/configuracoes/`
- **Administração** — `/v1/administracao/`
- **Automação WhatsApp** — disparo de mensagens de cobrança e confirmação de pagamento
- **Integração Pix** — geração de QR Code e recebimento de webhooks

## Estrutura do projeto
```
Brisa-Bigua/
├── src/
│   ├── manage.py
│   ├── buiga_utils.py       # Utilitários (validação de CPF)
│   ├── webapi/              # Configurações Django (settings, urls, wsgi)
│   └── v1/                  # App principal
│       ├── models.py        # Modelos de dados
│       ├── views.py         # Views
│       ├── urls.py          # Rotas
│       ├── static/          # CSS
│       └── templates/       # Templates HTML
├── prototipo/               # Protótipo visual inicial (referência)
```
