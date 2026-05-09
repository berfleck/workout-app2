"""Configuração declarativa dos pesos de proximidade entre exercícios.

Implementa as decisões fechadas na Etapa 6:
- Seção 8.10 (B): forma de armazenamento — dataclass + override por subregião
- Seção 8.11 (A): escala numérica unificada -100/-50/-20/-5
- Seção 1.5: escopo de aplicação ancorado em subregião
- Seção 1.7 (D1): hard INTRA fica no predicado `_compativel_intra`
  (gerador_treino.py); aqui só vivem soft INTRA, INTER e HISTÓRICO
- Seção 8.9 (D3): default INTER 0.80 + overrides; HIST integral quando ON

A função `_score_proximidade` que aplica esses pesos vive em
`gerador_treino.py` (decisão pré-Sessão 8). Este módulo é configuração
declarativa — mexe ao calibrar pesos, não ao mudar algoritmo.

A constante `SUBREGIOES_LATERALIDADE_HARD` é configuração da Etapa 6
referenciada pelo predicado D1.d (Seção 1.7) e mora aqui pra ficar
próxima das outras configs de proximidade.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# A.1 — Escala numérica unificada (Seção 8.11)
# ---------------------------------------------------------------------------

ESCALA_NUMERICA: dict[str, int] = {
    "soft_critico": -100,
    "soft_alto":     -50,
    "soft_medio":    -20,
    "soft_baixo":     -5,
}


# ---------------------------------------------------------------------------
# Hard contextual D1.d — referenciada pelo predicado `_compativel_intra`
# em gerador_treino.py (Seção 1.7). Promover novas subregiões a hard =
# adicionar ao frozenset.
# ---------------------------------------------------------------------------

SUBREGIOES_LATERALIDADE_HARD: frozenset[str] = frozenset({"costas"})


# ---------------------------------------------------------------------------
# B — Estrutura de configuração (Seção 8.10 / Opção 1 detalhada)
# ---------------------------------------------------------------------------


@dataclass
class PesoDim:
    """Pesos de uma dimensão de proximidade nos 3 contextos.

    `intra_overrides` aplica override por subregião (Seção 1.5).
    Valor `None` em override sinaliza "dim NÃO se aplica" — caller
    deve skip silenciosamente (return 0 penalty).

    INTER usa multiplicador global (D3.1 = 0.8) com `inter_override`
    pontual (ex: variante_pontual = 0.95, Soft Crítico).

    HISTÓRICO usa multiplicador integral 1.0 quando toggle ON (D3.3);
    quem dispara HIST é o caller checando match nome/família R-1.
    """

    intra_default: str
    intra_overrides: dict[str, Optional[str]] = field(default_factory=dict)
    inter_multiplicador: float = 0.8
    inter_override: Optional[float] = None
    historico_r1_multiplicador: float = 1.0

    def label_intra(self, subregiao: Optional[str]) -> Optional[str]:
        """Label INTRA pra subregião dada. `None` = dim N/A nessa subregião."""
        if subregiao is not None and subregiao in self.intra_overrides:
            return self.intra_overrides[subregiao]
        return self.intra_default

    def peso_intra(self, subregiao: Optional[str]) -> int:
        """Resolve label INTRA → número via ESCALA_NUMERICA (0 se N/A)."""
        label = self.label_intra(subregiao)
        if label is None:
            return 0
        return ESCALA_NUMERICA[label]

    def peso_inter(self, subregiao: Optional[str]) -> float:
        """Peso INTER = peso INTRA × multiplicador (override ou global)."""
        intra = self.peso_intra(subregiao)
        if intra == 0:
            return 0.0
        mult = (
            self.inter_override
            if self.inter_override is not None
            else self.inter_multiplicador
        )
        return intra * mult

    def peso_historico(self, subregiao: Optional[str]) -> float:
        """Peso HISTÓRICO R-1 = peso INTRA × multiplicador (1.0 quando ON)."""
        intra = self.peso_intra(subregiao)
        if intra == 0:
            return 0.0
        return intra * self.historico_r1_multiplicador


# ---------------------------------------------------------------------------
# Subregiões onde cada dim NÃO se aplica (derivado de Seção 7 / 8.15.2)
# ---------------------------------------------------------------------------

# Pegada N/A em squats, hinges, knee_flex, tríceps/bíceps, pranchas (core).
# Seção 7.3 / item 12.
_SUBREGIOES_PEGADA_NA: tuple[str, ...] = (
    "perna_anterior",   # squats
    "perna_posterior",  # hinges + knee_flex
    "adutores",
    "panturrilha",
    "bracos",           # tríceps + bíceps
    "core_isometrico",
    "core_dinamico",
    "cardio",
)

# Plano corporal N/A em squats e core (Seção 7.4 / item 13). Em puxadas
# tag só aparece em Pullover/Pulldown — a dim "vive" em costas com peso
# único (decisão Sessão 8: aceitar limitação de granularidade por
# subregião pra remadas vs puxadas).
_SUBREGIOES_PLANO_NA: tuple[str, ...] = (
    "perna_anterior",   # squats
    "adutores",
    "panturrilha",
    "core_isometrico",
    "core_dinamico",
    "cardio",
)

# Equipamento N/A em core (Seção 7.2 / item 9-bis Sessão 7c).
_SUBREGIOES_EQUIPAMENTO_NA: tuple[str, ...] = (
    "core_isometrico",
    "core_dinamico",
    "cardio",
)


# ---------------------------------------------------------------------------
# B.2 — Estrutura paralela ortogonal: anti_uni_mesmo_grupo da Etapa 5
# ---------------------------------------------------------------------------
# Peso por grupo musculo-funcional (Etapa 5 GRUPO_MUSCULAR_PADRAO).
# Default -75 pra todos os grupos (mantém comportamento validado em 5.2).
# Calibração C 7.6 pode ajustar global ou por grupo específico.

ANTI_UNI_GRUPOS_PADRAO: tuple[str, ...] = (
    "push", "pull", "quad", "hamstring", "glute",
    "addutor", "calf", "core", "cardio",
)

ANTI_UNI_PESO_DEFAULT: float = -75.0


# ---------------------------------------------------------------------------
# Config principal (B + A + Defaults derivados de Seção 2)
# ---------------------------------------------------------------------------


@dataclass
class ConfigPesosProximidade:
    """Configuração completa de pesos de proximidade.

    Hierarquia de lookup (B.2): override por subregião → default global,
    via `PesoDim.label_intra()`.

    `anti_uni_mesmo_grupo_pesos` é estrutura paralela ortogonal (peso por
    grupo musculo-funcional, fora da escala unificada — decisão A.2).

    HARD parts (família estrita, variante_pontual, lateralidade contextual
    costas) NÃO vivem aqui — vivem no predicado `_compativel_intra` em
    gerador_treino.py (Seção 1.7). Aqui só ficam soft INTRA + INTER +
    HISTÓRICO (incluindo INTER soft alto da família e INTER Soft Crítico
    da variante_pontual).
    """

    familia_estrita: PesoDim
    pegada: PesoDim
    plano_corporal: PesoDim
    equipamento_grupo: PesoDim
    variante_pontual: PesoDim

    anti_uni_mesmo_grupo_pesos: dict[str, float] = field(default_factory=dict)


def _config_default() -> ConfigPesosProximidade:
    """Constrói config default — valores de Seções 2-7-8 (Etapa 6)."""

    return ConfigPesosProximidade(
        # familia_estrita: hard INTRA fica no predicado; INTRA label =
        # soft_alto (-50) é a base numérica para INTER/HIST conforme tabela
        # da Seção 8.11 A.3 — INTER 0.80 → -40; HIST 1.0 → -50; pior caso
        # INTER+HIST = -90, preservando semântica "soft alto < padrao_diff
        # +100" (Seção 1.4). Decisão Sessão 8 fechou contradição entre
        # 8.15.2 (que dizia soft_critico) e 8.11 A.3 (que ancorava -90 pior
        # caso) em favor de A.3.
        familia_estrita=PesoDim(
            intra_default="soft_alto",
            inter_multiplicador=0.8,
            historico_r1_multiplicador=1.0,
        ),
        # pegada: Alto INTRA, N/A em squats/hinges/knee_flex/tríceps/core.
        pegada=PesoDim(
            intra_default="soft_alto",
            intra_overrides={s: None for s in _SUBREGIOES_PEGADA_NA},
            inter_multiplicador=0.8,
            historico_r1_multiplicador=1.0,
        ),
        # plano_corporal: Alto INTRA, N/A em squats/core.
        plano_corporal=PesoDim(
            intra_default="soft_alto",
            intra_overrides={s: None for s in _SUBREGIOES_PLANO_NA},
            inter_multiplicador=0.8,
            historico_r1_multiplicador=1.0,
        ),
        # equipamento_grupo: Baixo INTRA tiebreaker, N/A em core (item 9-bis).
        equipamento_grupo=PesoDim(
            intra_default="soft_baixo",
            intra_overrides={s: None for s in _SUBREGIOES_EQUIPAMENTO_NA},
            inter_multiplicador=0.8,
            historico_r1_multiplicador=1.0,
        ),
        # variante_pontual: Crítico INTRA (hard predicado), Soft Crítico
        # INTER 0.95 explícito (D1.c).
        variante_pontual=PesoDim(
            intra_default="soft_critico",
            inter_multiplicador=0.8,
            inter_override=0.95,
            historico_r1_multiplicador=1.0,
        ),
        anti_uni_mesmo_grupo_pesos={
            grupo: ANTI_UNI_PESO_DEFAULT for grupo in ANTI_UNI_GRUPOS_PADRAO
        },
    )


PESOS_DEFAULT: ConfigPesosProximidade = _config_default()


__all__ = [
    "ESCALA_NUMERICA",
    "SUBREGIOES_LATERALIDADE_HARD",
    "PesoDim",
    "ConfigPesosProximidade",
    "ANTI_UNI_GRUPOS_PADRAO",
    "ANTI_UNI_PESO_DEFAULT",
    "PESOS_DEFAULT",
]
