from django.urls import path

from .views import (
    teste_bot,
    testar_scheduler,
    painel_configuracao,
    painel_historico,
    painel_templates,
    painel_template_editar,
    painel_template_usar,
)
from .webhooks import webhook

urlpatterns = [
    path("teste/", teste_bot),
    path("scheduler/", testar_scheduler),
    path("webhook/", webhook),
    path("painel/configuracao/", painel_configuracao, name="whatsapp-configuracao"),
    path("painel/historico/", painel_historico, name="whatsapp-historico"),
    path("painel/templates/", painel_templates, name="whatsapp-templates"),
    path("painel/templates/<int:template_id>/editar/", painel_template_editar, name="whatsapp-template-editar"),
    path("painel/templates/<int:template_id>/usar/", painel_template_usar, name="whatsapp-template-usar"),
]
