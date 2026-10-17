from django.db import connection
from django.http import JsonResponse


def health(request):
    """Endpoint simples para monitoramento do processo e do banco."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"status": "unhealthy"}, status=503)
