# -*- coding: utf-8 -*-
"""Publicação da PÁGINA DO ALUNO no Cloudflare Pages (feature de mídia, Fase 2).

Fluxo de `publicar_rotina(rotina_id)`:
  1. carrega a rotina (historico) + gera o HTML (pagina_aluno)
  2. escreve em publicado/<slug>.html  (slug determinístico e inadivinhável)
  3. garante que o projeto Pages existe (cria via API se não)
  4. faz deploy da pasta publicado/ via `npx wrangler pages deploy`
  5. retorna a URL pública: https://<project>.pages.dev/<slug>

Credenciais em cloudflare_config.json (gitignorado). Nenhum segredo no código.
"""
import hashlib
import json
import os
import secrets
import subprocess

import requests

import database
import pagina_aluno

_RAIZ = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH = os.path.join(_RAIZ, "cloudflare_config.json")
_PUBLICADO_DIR = os.path.join(_RAIZ, "publicado")
_API = "https://api.cloudflare.com/client/v4"


class PublicacaoErro(Exception):
    pass


def _config():
    if not os.path.exists(_CONFIG_PATH):
        raise PublicacaoErro("cloudflare_config.json não encontrado.")
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        c = json.load(f)
    for k in ("account_id", "api_token", "project_name"):
        if not c.get(k) or "AQUI" in str(c[k]) or "SEU_" in str(c[k]):
            raise PublicacaoErro(f"cloudflare_config.json: campo '{k}' não preenchido.")
    # salt determinístico do slug — gera e persiste na 1a vez
    if not c.get("slug_salt"):
        c["slug_salt"] = secrets.token_hex(16)
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(c, f, ensure_ascii=False, indent=2)
    return c


def _headers(c):
    return {"Authorization": f"Bearer {c['api_token']}"}


def verificar_token(c=None):
    """Valida o token. Retorna (ok: bool, msg: str)."""
    c = c or _config()
    try:
        r = requests.get(f"{_API}/user/tokens/verify", headers=_headers(c), timeout=20)
        j = r.json()
        if r.ok and j.get("success"):
            return True, "Token válido."
        return False, f"Token inválido: {j.get('errors')}"
    except requests.RequestException as e:
        return False, f"Erro de rede: {e}"


def _slug(c, rotina_id):
    h = hashlib.sha256(f"{c['slug_salt']}:{rotina_id}".encode()).hexdigest()
    return h[:14]


def _ensure_project(c):
    """Cria o projeto Pages (Direct Upload) se ainda não existir."""
    nome = c["project_name"]
    url = f"{_API}/accounts/{c['account_id']}/pages/projects/{nome}"
    r = requests.get(url, headers=_headers(c), timeout=20)
    if r.ok and r.json().get("success"):
        return  # já existe
    # cria
    r = requests.post(
        f"{_API}/accounts/{c['account_id']}/pages/projects",
        headers=_headers(c),
        json={"name": nome, "production_branch": "main"},
        timeout=30)
    j = r.json()
    if not (r.ok and j.get("success")):
        raise PublicacaoErro(f"Falha ao criar projeto Pages: {j.get('errors')}")


def _deploy(c):
    """Deploy da pasta publicado/ via wrangler (npx). Retorna stdout."""
    env = dict(os.environ)
    env["CLOUDFLARE_API_TOKEN"] = c["api_token"]
    env["CLOUDFLARE_ACCOUNT_ID"] = c["account_id"]
    cmd = (f'npx --yes wrangler pages deploy "{_PUBLICADO_DIR}" '
           f'--project-name {c["project_name"]} --branch main --commit-dirty=true')
    proc = subprocess.run(cmd, shell=True, env=env, capture_output=True,
                          encoding="utf-8", errors="replace", cwd=_RAIZ, timeout=300)
    if proc.returncode != 0:
        raise PublicacaoErro(f"wrangler falhou:\n{proc.stdout}\n{proc.stderr}")
    return proc.stdout


def publicar_rotina(rotina_id, aluno_nome=None, nomes_treinos=None):
    """Gera e publica a página da rotina. Retorna a URL pública."""
    c = _config()
    reg = database.carregar_registro(rotina_id)
    if not reg:
        raise PublicacaoErro(f"Rotina {rotina_id} não encontrada.")
    nome = aluno_nome or reg.get("aluno") or "Aluno"
    html = pagina_aluno.gerar_html_de_sessoes(
        reg["sessoes"], nome, nomes_treinos=nomes_treinos)

    os.makedirs(_PUBLICADO_DIR, exist_ok=True)
    slug = _slug(c, str(rotina_id))
    with open(os.path.join(_PUBLICADO_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)

    _ensure_project(c)
    _deploy(c)
    return f"https://{c['project_name']}.pages.dev/{slug}"


def url_da_rotina(rotina_id):
    """URL pública esperada de uma rotina (sem publicar). None se sem config."""
    try:
        c = _config()
    except PublicacaoErro:
        return None
    return f"https://{c['project_name']}.pages.dev/{_slug(c, str(rotina_id))}"
