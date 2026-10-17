from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("whatsapp", "0008_configuracaowhatsapp_idioma_template_cobranca_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="TemplateWhatsApp",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("meta_id", models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ("nome", models.CharField(max_length=100)),
                ("idioma", models.CharField(default="pt_BR", max_length=20)),
                ("categoria", models.CharField(default="UTILITY", max_length=30)),
                ("corpo", models.TextField()),
                ("status", models.CharField(choices=[("PENDING", "Pendente"), ("APPROVED", "Aprovado"), ("REJECTED", "Rejeitado"), ("PAUSED", "Pausado"), ("DISABLED", "Desativado"), ("UNKNOWN", "Desconhecido")], default="UNKNOWN", max_length=20)),
                ("componentes", models.JSONField(blank=True, default=list)),
                ("ultima_sincronizacao", models.DateTimeField(blank=True, null=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["nome", "idioma"]},
        ),
        migrations.AddConstraint(
            model_name="templatewhatsapp",
            constraint=models.UniqueConstraint(fields=("nome", "idioma"), name="whatsapp_template_nome_idioma_unico"),
        ),
    ]
