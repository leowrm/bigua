from django.contrib import admin

from .models import (
    ConversaWhatsApp,
    EstadoConversa,
    DisparoWhatsApp,
    ConfiguracaoWhatsApp,
    TemplateWhatsApp,
)

admin.site.register(ConversaWhatsApp)
admin.site.register(ConfiguracaoWhatsApp)
admin.site.register(EstadoConversa)
admin.site.register(DisparoWhatsApp)
admin.site.register(TemplateWhatsApp)
