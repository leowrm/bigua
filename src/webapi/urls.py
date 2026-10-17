from django.contrib import admin
from django.urls import include, path
from .health import health
from v1.views import landing

urlpatterns = [
    path('', landing, name='landing'),
    path('health/', health, name='health'),
    path('admin/', admin.site.urls),
    path('v1/', include('v1.urls')),
    path('whatsapp/', include('whatsapp.urls')),
]
