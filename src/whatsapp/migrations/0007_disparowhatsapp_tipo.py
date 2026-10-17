from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('whatsapp', '0006_disparowhatsapp_mensalidade'),
    ]

    operations = [
        migrations.AddField(
            model_name='disparowhatsapp',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('PRE_VENCIMENTO', 'Pré-vencimento'),
                    ('VENCIMENTO', 'Vencimento'),
                    ('ATRASO', 'Atraso'),
                ],
                default='PRE_VENCIMENTO',
                max_length=30,
            ),
        ),
    ]