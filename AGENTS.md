# Brisa-Biguá — Contexto do projeto

## Objetivo

Sistema web de gestão da Associação de Canoagem e Preservação Ambiental Biguá.
O sistema gerencia associados, planos, mensalidades, cobranças e integrações com
WhatsApp. A versão atual é específica para a ONG Biguá; uma futura versão poderá
ser adaptada para um produto white label.

## Stack

- Backend: Python 3.13 e Django 5.2.
- Banco local: SQLite, arquivo `src/mydatabase`.
- Banco recomendado em produção: PostgreSQL.
- SQLite pode ser usado em uma instalação pequena e com pouco acesso simultâneo,
  mas não é a opção recomendada para os jobs de cobrança e WhatsApp.
- Frontend: templates Django, HTML, CSS e pequenos scripts JavaScript inline.
- Node.js, React e npm não fazem parte da execução atual.
- WhatsApp: WhatsApp Cloud API da Meta.
- Produção: Ubuntu 24.04, Gunicorn, Nginx e HTTPS via Let's Encrypt.
- Jobs de cobrança e WhatsApp: cron externo; o scheduler interno fica desligado.

## Estrutura principal

- `src/manage.py`: comandos do Django.
- `src/webapi/`: configurações, URLs e WSGI.
- `src/v1/`: módulo principal, modelos, views, templates e telas administrativas.
- `src/whatsapp/`: configuração, templates, histórico, webhook e serviços do WhatsApp.
- `src/v1/static/landing/`: imagens da landing page da ONG.
- `deploy/`: arquivos de systemd e Nginx para produção.
- `public/`: arquivos públicos auxiliares.

## Rodar localmente no Windows

No PowerShell:

```powershell
cd "C:\Users\wesle\bigua\src"
Copy-Item .env.example .env
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000 --no-color
```

A aplicação fica em:

`http://127.0.0.1:8000/v1/`

Para criar um administrador local:

```powershell
python manage.py createsuperuser
```

O ambiente local usa `src/.env`. Nunca substituir esse arquivo por credenciais
de produção nem versioná-lo.

## Configuração local

Para desenvolvimento, usar:

- `DJANGO_DEBUG=True`
- `DB_ENGINE=sqlite3`
- `DJANGO_SECURE_SSL_REDIRECT=False`
- `DJANGO_HSTS_SECONDS=0`
- `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`

Tokens da Meta, senha do banco, `DJANGO_SECRET_KEY` real e outros segredos nunca
devem ser escritos neste arquivo de contexto, em commits ou em mensagens.

## Produção atual

- Hospedagem: VPS Hostinger.
- Sistema: Ubuntu 24.04 LTS.
- Domínio: `ongbigua.online`.
- IP da VPS: consultar o painel da Hostinger; não duplicar esse dado em novos
  documentos públicos se não for necessário.
- Projeto remoto: `/opt/bigua`.
- Código Django remoto: `/opt/bigua/src`.
- Usuário do serviço: `bigua`.
- Ambiente virtual remoto: `/opt/bigua/.venv`.
- Serviço: `bigua.service`.
- Proxy: Nginx.
- Certificado: Let's Encrypt administrado pelo Certbot.

Após enviar alterações Python ou templates para a VPS:

```bash
cd /opt/bigua/src
sudo -u bigua /opt/bigua/.venv/bin/python manage.py migrate
sudo systemctl restart bigua
sudo systemctl status bigua --no-pager
```

Se a produção usar SQLite, não é necessário executar comandos do PostgreSQL.
Mantenha um único worker do Gunicorn e faça backup do arquivo `src/mydatabase`.
O SQLite é aceitável para uma instalação pequena, mas pode apresentar bloqueios
quando o painel, o cron e o WhatsApp escreverem ao mesmo tempo.

Após alterar arquivos estáticos:

```bash
sudo -u bigua /opt/bigua/.venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart bigua
```

Não alterar o `.env` de produção sem confirmar a variável e o valor corretos.

## Regras funcionais importantes

### Permissões

- Administração é uma permissão separada.
- WhatsApp deve ser uma permissão separada de Administração.
- O checkbox do WhatsApp usa o valor `view_configuracaowhatsapp`.
- Usuários comuns só devem ver as telas do WhatsApp quando receberem essa
  permissão.
- Usuários `staff` continuam com acesso administrativo e ao WhatsApp.
- Ao alterar permissões, proteger também as URLs/views, não apenas a sidebar.

### Experiência dos formulários

- Erros de validação não devem apagar os campos já preenchidos.
- Manter valores e checkboxes enviados ao renderizar o formulário novamente.
- Não repopular senhas após erro.
- Destacar o campo inválido quando possível.
- Validar CPF, telefone, e-mail e dia de cobrança sem perder os demais dados.

### WhatsApp

O fluxo planejado possui:

1. Envio ativo de lembretes de mensalidades abertas.
2. Resposta automática a mensagens recebidas com menu numérico:
   - consultar mensalidades abertas;
   - realizar doação unitária por chave Pix fixa;
   - falar com atendente, redirecionando para o WhatsApp da ONG.

Não adicionar pagamentos automáticos sem solicitação explícita. A chave Pix da
ONG é o CNPJ, mas o valor real deve ser mantido em configuração segura quando
for usado em produção.

O envio de cobranças possui os comandos `gerar_disparos_whatsapp` e
`enviar_disparos_whatsapp`. O primeiro cria registros `AGENDADO`; o segundo
envia pela Cloud API e atualiza para `ENVIADO` ou `FALHOU`. A rotina usa o campo
`Mensalidades.vencimento`.

## Landing page

- Paleta: laranja, preto e branco.
- Deve usar as fotos fornecidas pela ONG e a logo oficial.
- Evitar avisos internos, placeholders e instruções de configuração visíveis ao
  público.
- Conferir caminhos dos arquivos estáticos depois de `collectstatic`.
- Informações institucionais devem ser confirmadas antes de publicar.

## Verificação antes de entregar alterações

Executar no mínimo:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test --verbosity 2
```

Quando houver alterações de templates:

```powershell
python manage.py shell -c "from django.template.loader import get_template; [get_template(x) for x in ['app.html','administracao.html','editar-usuario.html']]; print('templates ok')"
```

Testar manualmente:

- login;
- cadastro com erro de validação;
- cadastro de associado mantendo os campos preenchidos;
- cadastro e edição de usuário;
- permissão WhatsApp separada de Administração;
- acesso negado a URLs do WhatsApp para usuário sem permissão;
- landing page e imagens;
- webhook somente quando o túnel/HTTPS estiver configurado.

## Cuidados para o próximo agente

- Não apagar a pasta `src` externa nem mover arquivos sem confirmar os imports.
- Não editar ou substituir `.env` de produção.
- Não usar `git reset --hard` ou apagar arquivos sem autorização.
- Preservar alterações existentes que não estejam relacionadas à tarefa atual.
- Usar `apply_patch` para edições locais.
- Antes de publicar, revisar `git diff` ou comparar os arquivos enviados para a VPS.
- Nunca incluir tokens da Meta, senhas, chaves privadas ou credenciais em commits.
