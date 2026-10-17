from django.apps import AppConfig
from django.conf import settings

class V1Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'v1'

    def ready(self):
        if getattr(settings, "ENABLE_BACKGROUND_SCHEDULER", False):
            from .scheduler import start
            start()
