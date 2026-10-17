import logging
import os

import requests
from django.utils import timezone

from .models import TemplateWhatsApp


logger = logging.getLogger(__name__)

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
WHATSAPP_WABA_ID = os.environ.get("WHATSAPP_WABA_ID")
WHATSAPP_API_VERSION = os.environ.get("WHATSAPP_API_VERSION", "v23.0")
BASE_URL = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"


class TemplateManagerError(Exception):
    pass


def _headers():
    if not WHATSAPP_TOKEN or not WHATSAPP_WABA_ID:
        raise TemplateManagerError(
            "Configure WHATSAPP_TOKEN e WHATSAPP_WABA_ID para administrar templates."
        )
    return {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }


def _request(method, url, **kwargs):
    try:
        response = requests.request(method, url, headers=_headers(), timeout=20, **kwargs)
    except requests.RequestException as exc:
        raise TemplateManagerError(f"Falha de conexão com a Meta: {exc}") from exc

    if not response.ok:
        try:
            detail = response.json().get("error", {}).get("message", response.text)
        except ValueError:
            detail = response.text
        raise TemplateManagerError(f"Meta recusou a operação: {detail}")
    return response.json()


def _corpo_do_template(data):
    for componente in data.get("components", []):
        if componente.get("type", "").upper() == "BODY":
            return componente.get("text", "")
    return ""


def _salvar_template(data):
    nome = data.get("name")
    idioma = data.get("language", "pt_BR")
    if not nome:
        return None
    defaults = {
        "meta_id": data.get("id"),
        "categoria": data.get("category", "UTILITY"),
        "corpo": _corpo_do_template(data),
        "status": data.get("status", "UNKNOWN").upper(),
        "componentes": data.get("components", []),
        "ultima_sincronizacao": timezone.now(),
    }
    template, _ = TemplateWhatsApp.objects.update_or_create(
        nome=nome,
        idioma=idioma,
        defaults=defaults,
    )
    return template


def sincronizar_templates():
    data = _request("GET", f"{BASE_URL}/{WHATSAPP_WABA_ID}/message_templates")
    templates = [_salvar_template(item) for item in data.get("data", [])]
    return [item for item in templates if item]


def criar_template(nome, idioma, categoria, corpo, exemplos=None):
    componente_corpo = {"type": "BODY", "text": corpo}
    if exemplos:
        componente_corpo["example"] = {"body_text": [exemplos]}
    data = _request(
        "POST",
        f"{BASE_URL}/{WHATSAPP_WABA_ID}/message_templates",
        json={
            "name": nome,
            "language": idioma,
            "category": categoria,
            "components": [componente_corpo],
        },
    )
    data.setdefault("name", nome)
    data.setdefault("language", idioma)
    data.setdefault("category", categoria)
    data.setdefault("components", [componente_corpo])
    return _salvar_template(data)


def editar_template(template, corpo, categoria=None, exemplos=None):
    if not template.meta_id:
        raise TemplateManagerError("Esse template ainda não possui ID na Meta.")
    componentes = template.componentes or [{"type": "BODY", "text": corpo}]
    componentes = [dict(item) for item in componentes]
    body = next((item for item in componentes if item.get("type", "").upper() == "BODY"), None)
    if body is None:
        componentes.append({"type": "BODY", "text": corpo})
    else:
        body["text"] = corpo
        if exemplos:
            body["example"] = {"body_text": [exemplos]}

    data = _request(
        "POST",
        f"{BASE_URL}/{template.meta_id}",
        json={
            "category": categoria or template.categoria,
            "components": componentes,
        },
    )
    template.corpo = corpo
    template.componentes = componentes
    template.categoria = categoria or template.categoria
    template.status = data.get("status", "PENDING").upper()
    template.ultima_sincronizacao = timezone.now()
    template.save()
    return template
