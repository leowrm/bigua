# Deploy da versão Biguá na VPS Hostinger

Esta versão é uma instalação dedicada da Biguá. Ela não é multi-tenant.

## Preparação

1. Use Python 3.12 ou superior. PostgreSQL é recomendado em produção; SQLite é
   uma alternativa para uma instalação pequena e com baixo acesso simultâneo.
2. Crie um ambiente virtual e instale `src/requirements.txt`.
3. Configure as variáveis de `src/.env.example` no provedor de hospedagem.
4. Gere uma `DJANGO_SECRET_KEY` nova e mantenha-a fora do repositório.
5. Configure um domínio com HTTPS e inclua-o em `DJANGO_ALLOWED_HOSTS` e `DJANGO_CSRF_TRUSTED_ORIGINS`.

## 1. Criar a VPS

No painel da Hostinger:

1. Crie uma VPS Linux com Ubuntu 22.04 ou 24.04.
2. Anote o IP público da VPS.
3. Crie um registro DNS `A` apontando o domínio para esse IP. Faça o mesmo para `www`, se for usar.
4. Acesse a VPS por SSH usando o usuário `root` inicialmente.

No computador local, compacte o projeto e envie-o para a VPS. Exemplo usando PowerShell:

```powershell
scp -r .\Brisa-Bigua-release root@IP_DA_VPS:/opt/
```

Na VPS, os comandos abaixo deixam o projeto em `/opt/bigua`:

```bash
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx git
mv /opt/Brisa-Bigua-release /opt/bigua
useradd --system --create-home --home-dir /opt/bigua --shell /usr/sbin/nologin bigua || true
chown -R bigua:bigua /opt/bigua
cd /opt/bigua
sudo -u bigua python3 -m venv .venv
sudo -u bigua .venv/bin/pip install --upgrade pip
sudo -u bigua .venv/bin/pip install -r src/requirements.txt
```

## 2. Escolher o banco de produção

### Opção recomendada: PostgreSQL

Instale o PostgreSQL:

```bash
apt install -y postgresql postgresql-contrib
```

Crie o usuário e o banco. Escolha uma senha forte e substitua
`SENHA_DO_BANCO`:

Escolha uma senha forte e substitua `SENHA_DO_BANCO` no comando:

```bash
sudo -u postgres psql
```

```sql
CREATE USER bigua WITH PASSWORD 'SENHA_DO_BANCO';
CREATE DATABASE bigua OWNER bigua;
\q
```

O PostgreSQL ficará acessível apenas localmente; não abra a porta 5432 no firewall.

### Opção alternativa: SQLite

Para uma ONG pequena, com cerca de 50 associados e pouco acesso simultâneo, é
possível usar SQLite na VPS. Nesse caso:

- não crie usuário ou banco PostgreSQL;
- use um único worker do Gunicorn;
- mantenha os jobs do WhatsApp no cron externo;
- faça backup do arquivo `/opt/bigua/src/mydatabase`;
- evite várias rotinas escrevendo no banco ao mesmo tempo;
- migre para PostgreSQL se surgirem bloqueios, lentidão ou mais usuários.

SQLite reduz a configuração, mas não oferece a mesma segurança operacional do
PostgreSQL para escritas concorrentes e crescimento do sistema.

## 3. Configurar as variáveis

Crie `/opt/bigua/src/.env` e preencha os valores reais. Gere a chave Django com:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Modelo mínimo:

```dotenv
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=COLE_A_CHAVE_GERADA
DJANGO_ALLOWED_HOSTS=SEU_DOMINIO,www.SEU_DOMINIO
DJANGO_CSRF_TRUSTED_ORIGINS=https://SEU_DOMINIO,https://www.SEU_DOMINIO
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_HSTS_SECONDS=31536000
# PostgreSQL (recomendado):
# DB_ENGINE=postgresql
# DB_NAME=bigua
# DB_USER=bigua
# DB_PASSWORD=SENHA_DO_BANCO
# DB_HOST=localhost
# DB_PORT=5432

# SQLite (alternativa):
DB_ENGINE=sqlite3
SQLITE_NAME=mydatabase
ENABLE_BACKGROUND_SCHEDULER=False
WHATSAPP_TOKEN=SEU_TOKEN
WHATSAPP_PHONE_NUMBER_ID=SEU_ID
WHATSAPP_WABA_ID=SEU_WABA_ID
WHATSAPP_VERIFY_TOKEN=SEU_TOKEN_DE_VERIFICACAO
WHATSAPP_API_VERSION=v23.0
```

Proteja o arquivo:

```bash
chown bigua:bigua /opt/bigua/src/.env
chmod 600 /opt/bigua/src/.env
```

## 4. Preparar o Django

```bash
cd /opt/bigua/src
sudo -u bigua .venv/bin/python manage.py migrate
sudo -u bigua .venv/bin/python manage.py collectstatic --noinput
sudo -u bigua .venv/bin/python manage.py createsuperuser
sudo -u bigua .venv/bin/python manage.py check --deploy
```

## 5. Ativar Gunicorn e Nginx

Copie os arquivos desta pasta de deploy:

```bash
cp /opt/bigua/deploy/bigua.service /etc/systemd/system/bigua.service
sed 's/SEU_DOMINIO_AQUI/SEU_DOMINIO/g' /opt/bigua/deploy/bigua-nginx.conf > /etc/nginx/sites-available/bigua
ln -sf /etc/nginx/sites-available/bigua /etc/nginx/sites-enabled/bigua
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl daemon-reload
systemctl enable --now bigua
systemctl restart nginx
```

Teste antes do HTTPS:

```bash
curl -I http://SEU_DOMINIO/health/
```

Ative o certificado:

```bash
certbot --nginx -d SEU_DOMINIO -d www.SEU_DOMINIO
```

Depois teste `https://SEU_DOMINIO/health/`.

## 6. Ativar os jobs de cobrança

Somente depois de testar o sistema, instale o cron:

```bash
crontab -u bigua /opt/bigua/deploy/bigua-cron
```

Confirme que `ENABLE_BACKGROUND_SCHEDULER=False`; não rode o scheduler interno e o cron ao mesmo tempo.

Para backup diário do PostgreSQL:

```bash
chmod +x /opt/bigua/deploy/backup-postgres.sh
cat /opt/bigua/deploy/bigua-backup-cron | crontab -u root -
```

Para backup do SQLite, faça uma cópia consistente do arquivo com a aplicação
temporariamente parada:

```bash
systemctl stop bigua
cp /opt/bigua/src/mydatabase /opt/bigua/backup-mydatabase-$(date +%F)
systemctl start bigua
```

## Primeira publicação

Execute dentro de `src/`:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
gunicorn webapi.wsgi:application --bind 0.0.0.0:8000
```

Teste `https://SEU_DOMINIO/health/` antes de configurar o webhook.

## Jobs de cobrança

O scheduler em background fica desligado por padrão para evitar duplicação com múltiplos workers. Configure um cron ou worker externo:

```cron
0 1 * * * cd /app/src && /app/.venv/bin/python manage.py shell -c "from buiga_utils import gerar_cobranças; gerar_cobranças()"
*/5 * * * * cd /app/src && /app/.venv/bin/python manage.py shell -c "from buiga_utils import verificar_cobrancas_atrasadas; verificar_cobrancas_atrasadas()"
*/5 * * * * cd /app/src && /app/.venv/bin/python manage.py gerar_disparos_whatsapp
*/5 * * * * cd /app/src && /app/.venv/bin/python manage.py enviar_disparos_whatsapp
```

Não habilite `ENABLE_BACKGROUND_SCHEDULER=True` ao mesmo tempo que esses jobs externos.

## WhatsApp Cloud API

Além do token e do ID do número, o painel de templates precisa do ID da conta
WhatsApp Business (WABA). Configure também `WHATSAPP_WABA_ID` e use um token
com as permissões de gerenciamento da conta WhatsApp Business. O menu
“Templates da Meta” permite sincronizar, criar e editar templates simples de
texto; a aprovação ou rejeição continua sendo processada pela Meta.

Configure no painel da Meta o webhook:

```text
https://SEU_DOMINIO/whatsapp/webhook/
```

Use o mesmo valor de `WHATSAPP_VERIFY_TOKEN` no painel da Meta e nas variáveis da aplicação. Antes de ativar cobranças reais, execute um envio de teste e confirme o recebimento do webhook.

## Operação mínima

- Faça backup diário do PostgreSQL.
- Monitore `/health/`, erros 5xx e falhas de envio.
- Não versione `.env`, tokens ou o banco local.
- Faça um teste de restauração do backup antes da entrega.
