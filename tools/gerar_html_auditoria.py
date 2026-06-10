"""Gera HTML standalone pra auditoria clínica de rotinas geradas pelo CSP.

Cards visuais (rotina > treino > bloco), 3 níveis de comentário
(bloco expansível, treino e rotina sempre visíveis), autosave em
localStorage, botões "Copiar JSON" e "Baixar .json".

Uso:
    python tools/gerar_html_auditoria.py

Saída: docs/auditoria/gate_<data>.html
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gerador_csp import gerar_rotina_csp, ConfigVariedade  # noqa: E402
from gerador_treino import carregar_banco  # noqa: E402


DATA_AUDITORIA = "2026-05-28"
DEMANDA_TREINO = [("regiao", "upper", 3), ("regiao", "lower", 3), ("regiao", "core", 2)]
N_TREINOS = 2
DEMANDAS = [DEMANDA_TREINO] * N_TREINOS
# Espelha o override do app (app_flask.py:_nivel_aluno_csp) — H-P1 desligado
# globalmente até maturidade do vetor de perfil (decisão 2026-05-28).
NIVEL_ALUNO = 3
SEEDS = [1040674188, 752055454, 2043474389, 53761357, 1896999516]

# Pesos defaults espelhando produção (app_flask.py)
from app_flask import (  # noqa: E402
    _PESO_SA1_DEFAULT, _PESO_SA1_REPET_DEFAULT, _PESO_SB5_DEFAULT,
    _PESO_SR1_DEFAULT, _PESO_SE1_PEGADA_DEFAULT, _PESO_SE1_PLANO_DEFAULT,
    _PESO_SE1_EQ_DEFAULT, _PESO_ST4_PEGADA_DEFAULT, _PESO_ST4_PLANO_DEFAULT,
    _PESO_ST4_EQ_DEFAULT, _PESO_EVITAR_AGONISTAS_DEFAULT,
    _PESO_TAMANHO_BLOCO_DEFAULT,
)

PESOS = dict(
    peso_evitar_agonistas=_PESO_EVITAR_AGONISTAS_DEFAULT,
    tamanho_preferido=2,
    peso_tamanho_bloco=_PESO_TAMANHO_BLOCO_DEFAULT,
    peso_sa1=_PESO_SA1_DEFAULT,
    peso_sa1_repet=_PESO_SA1_REPET_DEFAULT,
    peso_sb5=_PESO_SB5_DEFAULT,
    peso_sr1=_PESO_SR1_DEFAULT,
    peso_se1_pegada=_PESO_SE1_PEGADA_DEFAULT,
    peso_se1_plano=_PESO_SE1_PLANO_DEFAULT,
    peso_se1_eq=_PESO_SE1_EQ_DEFAULT,
    peso_st4_pegada=_PESO_ST4_PEGADA_DEFAULT,
    peso_st4_plano=_PESO_ST4_PLANO_DEFAULT,
    peso_st4_eq=_PESO_ST4_EQ_DEFAULT,
)


def _dim_or_none(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none"):
        return None
    return s


def _tag_tamanho(n):
    return {1: "solo", 2: "par", 3: "trio"}.get(n, f"{n}-ex")


def _render_exercicio(ex):
    nome = html.escape((ex.nome or "").strip())
    sub = html.escape(ex.subregiao or "—")
    pad = html.escape(ex.padrao or "—")
    lat_raw = (ex.unilateral or "").strip()
    lat = "uni" if lat_raw == "unilateral" else ("bi" if lat_raw == "bilateral" else "—")
    lat_cls = "lat-uni" if lat == "uni" else "lat-bi" if lat == "bi" else "lat-na"

    dims = []
    for label, v in (
        ("pegada", _dim_or_none(ex.pegada)),
        ("plano", _dim_or_none(ex.plano_corporal)),
        ("eq", _dim_or_none(ex.equipamento_grupo)),
    ):
        if v:
            dims.append(f'<span class="dim"><span class="dim-key">{label}</span> {html.escape(v)}</span>')
    dims_html = "".join(dims)
    return f'''
        <div class="ex">
            <div class="ex-nome">{nome}</div>
            <div class="ex-meta">
                <span class="chip chip-sub">{sub}</span>
                <span class="chip chip-pad">{pad}</span>
                <span class="chip {lat_cls}">{lat}</span>
                {dims_html}
            </div>
        </div>
    '''


def _render_bloco(rotina_idx, treino_idx, bloco_label, bloco_exs):
    tamanho = _tag_tamanho(len(bloco_exs))
    ex_html = "\n".join(_render_exercicio(ex) for ex in bloco_exs)
    key = f"r{rotina_idx}.t{treino_idx}.{bloco_label}"
    return f'''
        <div class="bloco" data-key="{key}">
            <div class="bloco-header">
                <span class="bloco-label">Bloco {bloco_label}</span>
                <span class="bloco-tag">{tamanho}</span>
            </div>
            <div class="bloco-exs">{ex_html}</div>
            <button type="button" class="add-comment-btn" data-target="comment-{key}">+ comentário neste bloco</button>
            <div class="comment-area collapsed" id="comment-{key}">
                <textarea data-key="{key}" placeholder="Críticas/observações sobre este bloco..."></textarea>
            </div>
        </div>
    '''


def _render_treino(rotina_idx, treino_idx, treino_dict):
    blocos_html = []
    for bi, bloco in enumerate(treino_dict["blocos"]):
        label = chr(ord("A") + bi)
        blocos_html.append(_render_bloco(rotina_idx, treino_idx, label, bloco))
    key = f"r{rotina_idx}.t{treino_idx}.geral"
    return f'''
        <div class="treino">
            <h3>Treino {treino_idx}</h3>
            <div class="blocos">{"".join(blocos_html)}</div>
            <div class="comment-treino">
                <label for="text-{key}">Considerações do Treino {treino_idx}</label>
                <textarea data-key="{key}" id="text-{key}" placeholder="Achados que cruzam blocos deste treino..."></textarea>
            </div>
        </div>
    '''


def _render_rotina(rotina_idx, seed, rotina_dict):
    treinos_html = "".join(
        _render_treino(rotina_idx, ti, t)
        for ti, t in enumerate(rotina_dict["treinos"], start=1)
    )
    key = f"r{rotina_idx}.geral"
    return f'''
        <section class="rotina" id="rotina-{rotina_idx}">
            <h2>Rotina {rotina_idx} <span class="seed">seed {seed}</span></h2>
            {treinos_html}
            <div class="comment-rotina">
                <label for="text-{key}">Considerações da Rotina {rotina_idx}</label>
                <textarea data-key="{key}" id="text-{key}" placeholder="Achados que cruzam treinos desta rotina..."></textarea>
            </div>
        </section>
    '''


CSS = """
:root {
    --laranja: #e85d04;
    --fundo: #f9fafb;
    --card: #ffffff;
    --borda: #e5e7eb;
    --texto: #1f2937;
    --secundario: #6b7280;
    --uni: #d97706;
    --bi: #2563eb;
}
* { box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--fundo);
    color: var(--texto);
    margin: 0;
    padding: 24px;
    line-height: 1.45;
}
.container { max-width: 1100px; margin: 0 auto; }
h1 { margin-top: 0; color: var(--laranja); }
.meta {
    background: var(--card);
    border: 1px solid var(--borda);
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 18px;
    font-size: 13.5px;
    color: var(--secundario);
}
.meta strong { color: var(--texto); }
.actions-sticky {
    position: sticky;
    top: 0;
    background: var(--fundo);
    padding: 10px 0;
    z-index: 10;
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 16px;
    border-bottom: 1px solid var(--borda);
}
.actions-sticky button {
    background: var(--laranja);
    color: white;
    border: 0;
    padding: 9px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
}
.actions-sticky button:hover { opacity: 0.9; }
.actions-sticky button.secondary {
    background: var(--card);
    color: var(--texto);
    border: 1px solid var(--borda);
}
.actions-sticky .status { font-size: 12.5px; color: var(--secundario); margin-left: auto; }
.rotina {
    background: var(--card);
    border: 1px solid var(--borda);
    border-radius: 10px;
    padding: 20px 22px;
    margin-bottom: 26px;
}
.rotina h2 { margin-top: 0; }
.rotina .seed {
    font-size: 13px;
    color: var(--secundario);
    font-weight: 400;
    margin-left: 8px;
}
.treino { margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--borda); }
.treino:first-of-type { border-top: 0; padding-top: 0; }
.treino h3 { margin: 0 0 12px; font-size: 16px; color: var(--laranja); }
.blocos { display: flex; flex-direction: column; gap: 14px; }
.bloco {
    background: var(--fundo);
    border: 1px solid var(--borda);
    border-radius: 8px;
    padding: 12px 14px;
}
.bloco-header { display: flex; gap: 10px; align-items: center; margin-bottom: 8px; }
.bloco-label { font-weight: 600; font-size: 14px; }
.bloco-tag {
    font-size: 11px;
    background: var(--borda);
    padding: 2px 8px;
    border-radius: 10px;
    color: var(--secundario);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.bloco-exs { display: flex; flex-direction: column; gap: 6px; }
.ex {
    background: var(--card);
    border: 1px solid var(--borda);
    border-radius: 6px;
    padding: 8px 10px;
}
.ex-nome { font-weight: 500; font-size: 14.5px; }
.ex-meta { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 4px; align-items: center; }
.chip {
    font-size: 11px;
    padding: 2px 7px;
    border-radius: 10px;
    background: var(--borda);
    color: var(--secundario);
}
.chip-sub { background: #fef3c7; color: #92400e; }
.chip-pad { background: #e0e7ff; color: #3730a3; }
.lat-uni { background: rgba(217, 119, 6, 0.12); color: var(--uni); font-weight: 600; }
.lat-bi { background: rgba(37, 99, 235, 0.10); color: var(--bi); font-weight: 600; }
.lat-na { background: var(--borda); color: var(--secundario); }
.dim {
    font-size: 11px;
    padding: 2px 7px;
    border-radius: 10px;
    background: #ecfdf5;
    color: #065f46;
}
.dim-key { color: #047857; font-weight: 600; }
.add-comment-btn {
    background: none;
    border: 1px dashed var(--borda);
    color: var(--secundario);
    padding: 4px 10px;
    font-size: 12px;
    margin-top: 10px;
    border-radius: 6px;
    cursor: pointer;
}
.add-comment-btn:hover { background: var(--fundo); color: var(--laranja); border-color: var(--laranja); }
.add-comment-btn.open { color: var(--laranja); border-color: var(--laranja); border-style: solid; }
.comment-area { margin-top: 8px; transition: all 0.2s; }
.comment-area.collapsed { display: none; }
textarea {
    width: 100%;
    min-height: 60px;
    padding: 10px 12px;
    border: 1px solid var(--borda);
    border-radius: 6px;
    font-family: inherit;
    font-size: 13.5px;
    resize: vertical;
    line-height: 1.4;
}
textarea:focus { outline: 2px solid var(--laranja); outline-offset: -1px; border-color: var(--laranja); }
.comment-treino, .comment-rotina, .cross-rotina {
    margin-top: 16px;
    padding-top: 14px;
    border-top: 1px dashed var(--borda);
}
.comment-treino label, .comment-rotina label, .cross-rotina label {
    display: block;
    font-size: 13px;
    color: var(--secundario);
    font-weight: 600;
    margin-bottom: 6px;
}
.comment-rotina textarea { min-height: 80px; }
.cross-rotina {
    background: var(--card);
    border: 1px solid var(--borda);
    border-radius: 10px;
    padding: 18px 22px;
    margin-top: 24px;
}
.cross-rotina h2 { margin-top: 0; color: var(--laranja); }
.cross-rotina textarea { min-height: 100px; }
"""

JS = """
const STORAGE_KEY = 'gate_clinico_2026-05-28';

function coletarDados() {
    const dados = { data_auditoria: '__DATA__', textareas: {} };
    document.querySelectorAll('textarea[data-key]').forEach(ta => {
        if (ta.value.trim()) dados.textareas[ta.dataset.key] = ta.value;
    });
    return dados;
}

function salvarLocal() {
    const dados = coletarDados();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(dados));
    const stamp = document.getElementById('autosave-stamp');
    if (stamp) {
        const h = new Date().toLocaleTimeString();
        stamp.textContent = 'autosave ' + h;
    }
}

function carregarLocal() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    try {
        const dados = JSON.parse(raw);
        const items = dados.textareas || {};
        Object.entries(items).forEach(([key, val]) => {
            const ta = document.querySelector(`textarea[data-key="${key}"]`);
            if (!ta) return;
            ta.value = val;
            // Se for textarea de bloco e tem conteudo, expande
            if (key.match(/^r\\d+\\.t\\d+\\.[A-Z]$/)) {
                const area = ta.closest('.comment-area');
                if (area) {
                    area.classList.remove('collapsed');
                    const bloco = area.closest('.bloco');
                    const btn = bloco && bloco.querySelector('.add-comment-btn');
                    if (btn) btn.classList.add('open');
                }
            }
        });
    } catch (e) { console.warn('Erro ao carregar localStorage:', e); }
}

function copiarJson() {
    const dados = coletarDados();
    const str = JSON.stringify(dados, null, 2);
    navigator.clipboard.writeText(str).then(() => {
        const stamp = document.getElementById('autosave-stamp');
        if (stamp) stamp.textContent = 'copiado!';
    }).catch(err => alert('Erro ao copiar: ' + err));
}

function baixarJson() {
    const dados = coletarDados();
    const str = JSON.stringify(dados, null, 2);
    const blob = new Blob([str], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'gate___DATA__.json';
    a.click();
    URL.revokeObjectURL(url);
}

function limparTudo() {
    if (!confirm('Limpar todos os comentários e localStorage? Não pode desfazer.')) return;
    document.querySelectorAll('textarea[data-key]').forEach(ta => { ta.value = ''; });
    document.querySelectorAll('.comment-area').forEach(a => a.classList.add('collapsed'));
    document.querySelectorAll('.add-comment-btn').forEach(b => b.classList.remove('open'));
    localStorage.removeItem(STORAGE_KEY);
    const stamp = document.getElementById('autosave-stamp');
    if (stamp) stamp.textContent = 'limpo';
}

document.addEventListener('DOMContentLoaded', () => {
    carregarLocal();

    document.querySelectorAll('.add-comment-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const target = document.getElementById(btn.dataset.target);
            if (!target) return;
            target.classList.toggle('collapsed');
            btn.classList.toggle('open');
            if (!target.classList.contains('collapsed')) {
                const ta = target.querySelector('textarea');
                if (ta) ta.focus();
            }
        });
    });

    // autosave 1s após digitação
    let timer = null;
    document.addEventListener('input', e => {
        if (e.target.matches('textarea[data-key]')) {
            clearTimeout(timer);
            timer = setTimeout(salvarLocal, 1000);
        }
    });
});
"""


def main():
    banco = carregar_banco(str(ROOT / "banco_exercicios.xlsx"))
    banco = [e for e in banco if getattr(e, "ativo", True) is not False]

    rotinas_html = []
    for ri, seed in enumerate(SEEDS, start=1):
        # python_seed=seed pra reprodutibilidade total (resolve o achado da
        # rodada anterior: ConfigVariedade sem python_seed varia entre runs).
        r = gerar_rotina_csp(
            DEMANDAS, banco, nivel_aluno=NIVEL_ALUNO, seed=seed,
            variedade=ConfigVariedade(python_seed=seed),
            **PESOS,
        )
        if not r.get("viavel"):
            rotinas_html.append(
                f'<section class="rotina"><h2>Rotina {ri} — seed {seed}</h2>'
                f'<p><strong>INVIÁVEL</strong> — status={r.get("status")}</p></section>'
            )
            continue
        rotinas_html.append(_render_rotina(ri, seed, r))

    meta = f'''
        <div class="meta">
            <strong>Config:</strong> Full Body 2T região — <code>upper(3) + lower(3) + core(2)</code> × 2 treinos idênticos<br>
            <strong>Aluno:</strong> intermediario, perfil aderência média (peso_aderencia=0). <em>H-P1 (filtro por complexidade) DESLIGADO — pool máximo, todos exercícios elegíveis.</em><br>
            <strong>Motor:</strong> CSP pós-S-T4 (main, commit <code>abed2ab</code>)<br>
            <strong>Pesos:</strong> S-A1=12, S-A1-repet=10, S-B5=4, S-R1=4, S-E1=10/10/2, S-T4=12/12/3, evitar_agonistas=10, tamanho_bloco=5/pref=2<br>
            <strong>Seeds:</strong> {", ".join(str(s) for s in SEEDS)}
        </div>
    '''

    cross = '''
        <section class="cross-rotina">
            <h2>Padrões cross-rotina</h2>
            <label for="text-cross">Achados que aparecem em mais de uma rotina ou padrões agregados</label>
            <textarea data-key="cross" id="text-cross" placeholder="Padrões repetidos, viéses sistemáticos..."></textarea>
        </section>
    '''

    actions = '''
        <div class="actions-sticky">
            <button onclick="copiarJson()">Copiar JSON</button>
            <button class="secondary" onclick="baixarJson()">Baixar .json</button>
            <button class="secondary" onclick="limparTudo()">Limpar tudo</button>
            <span class="status" id="autosave-stamp">autosave inativo</span>
        </div>
    '''

    css_block = f'<style>{CSS}</style>'
    js_block = f'<script>{JS.replace("__DATA__", DATA_AUDITORIA)}</script>'

    html_out = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gate clínico semântico — {DATA_AUDITORIA}</title>
{css_block}
</head>
<body>
<div class="container">
    <h1>Gate clínico semântico — {DATA_AUDITORIA}</h1>
    {meta}
    {actions}
    {"".join(rotinas_html)}
    {cross}
</div>
{js_block}
</body>
</html>
'''

    out_path = ROOT / "docs" / "auditoria" / f"gate_{DATA_AUDITORIA}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_out, encoding="utf-8")
    print(f"OK: {out_path}")
    print(f"Tamanho: {len(html_out)} chars")


if __name__ == "__main__":
    main()
