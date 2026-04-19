"""
Gerador de imagem PNG do treino.
Usa Pillow para renderizar o treino com layout clean.
"""

from PIL import Image, ImageDraw, ImageFont
import io
import os

# Fontes — incluídas no repositório para garantir suporte a acentos
_BASE = os.path.dirname(os.path.abspath(__file__))
FONT_REG  = os.path.join(_BASE, "DejaVuSans.ttf")
FONT_BOLD = os.path.join(_BASE, "DejaVuSans-Bold.ttf")

# Fallback para sistema se não encontrar no repositório
if not os.path.exists(FONT_REG):
    FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Paleta
COR_BG        = (255, 255, 255)
COR_HEADER_BG = (17, 24, 39)       # cinza escuro
COR_HEADER_FG = (255, 255, 255)
COR_LABEL     = (156, 163, 175)    # cinza claro
COR_NOME      = (17, 24, 39)       # quase preto
COR_META      = (107, 114, 128)    # cinza médio
COR_BLOCO_BG  = (249, 250, 251)    # cinza muito claro
COR_DIVISOR   = (229, 231, 235)
COR_ACENTO    = (232, 93, 4)       # laranja

W = 800  # largura fixa


def carregar_fonte(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def text_height(font, texto="A"):
    bbox = font.getbbox(texto)
    return bbox[3] - bbox[1]


def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def gerar_png(sessao, nome_aluno: str, logo_bytes=None) -> bytes:
    """
    Gera PNG do treino e retorna os bytes.

    Args:
        sessao: objeto Sessao com blocos
        nome_aluno: nome do aluno para o cabeçalho
        logo_bytes: bytes da imagem da logo (opcional)
    """

    # Fontes
    f_titulo   = carregar_fonte(FONT_BOLD, 26)
    f_subtitulo= carregar_fonte(FONT_REG, 16)
    f_label    = carregar_fonte(FONT_BOLD, 11)
    f_ex_nome  = carregar_fonte(FONT_BOLD, 15)
    f_ex_meta  = carregar_fonte(FONT_REG, 13)
    f_prescr   = carregar_fonte(FONT_BOLD, 12)

    PAD    = 40
    PAD_SM = 20
    INNER  = W - PAD * 2

    # -----------------------------------------------------------------------
    # Primeiro passo: calcular altura total
    # -----------------------------------------------------------------------
    # Usamos um draw temporário para medir texto
    tmp = Image.new("RGB", (W, 100))
    draw_tmp = ImageDraw.Draw(tmp)

    altura = 0

    # Header
    HEADER_H = 90
    if logo_bytes:
        HEADER_H = 110
    altura += HEADER_H

    # Separador após header
    altura += 16

    # Blocos
    for bloco in sessao.blocos:
        exercicios = [e for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e]
        # Label do bloco
        altura += 28
        # Cada exercício
        for ex in exercicios:
            nome_lines = wrap_text(ex.nome, f_ex_nome, INNER - PAD_SM * 2, draw_tmp)
            altura += len(nome_lines) * (text_height(f_ex_nome) + 2)
            # Linha de prescrição se houver
            tem_prescricao = ex.series or ex.reps or ex.rir is not None
            if tem_prescricao:
                altura += text_height(f_prescr) + 4
            altura += 10  # padding entre exercícios
        altura += 16  # espaço após bloco

    # Rodapé
    altura += 40

    altura = max(altura, 400)

    # -----------------------------------------------------------------------
    # Segundo passo: renderizar
    # -----------------------------------------------------------------------
    img = Image.new("RGB", (W, altura), COR_BG)
    draw = ImageDraw.Draw(img)

    y = 0

    # --- Header ---
    draw.rectangle([(0, 0), (W, HEADER_H)], fill=COR_HEADER_BG)

    logo_w = 0
    if logo_bytes:
        try:
            logo_img = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
            lh = HEADER_H - 20
            ratio = lh / logo_img.height
            lw = int(logo_img.width * ratio)
            logo_img = logo_img.resize((lw, lh), Image.LANCZOS)
            # Fundo branco para logos com transparência
            logo_bg = Image.new("RGB", (lw, lh), COR_HEADER_BG)
            logo_bg.paste(logo_img, mask=logo_img.split()[3] if logo_img.mode == "RGBA" else None)
            img.paste(logo_bg, (PAD, 10))
            logo_w = lw + 20
        except Exception:
            logo_w = 0

    # Nome do aluno e título
    txt_x = PAD + logo_w
    nome_y = HEADER_H // 2 - text_height(f_titulo) - 4
    draw.text((txt_x, nome_y), nome_aluno, font=f_titulo, fill=COR_HEADER_FG)
    draw.text((txt_x, nome_y + text_height(f_titulo) + 6), "Treino personalizado", font=f_subtitulo, fill=(156, 163, 175))

    y = HEADER_H + 16

    # --- Blocos ---
    for bloco in sessao.blocos:
        exercicios = [e for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e]

        # Fundo do bloco
        ex_heights = []
        for ex in exercicios:
            nome_lines = wrap_text(ex.nome, f_ex_nome, INNER - PAD_SM * 2, draw)
            h = len(nome_lines) * (text_height(f_ex_nome) + 2)
            tem_prescricao = ex.series or ex.reps or ex.rir is not None
            if tem_prescricao:
                h += text_height(f_prescr) + 4
            h += 10
            ex_heights.append(h)

        bloco_h = 28 + sum(ex_heights) + 8
        draw.rounded_rectangle(
            [(PAD, y), (PAD + INNER, y + bloco_h)],
            radius=10,
            fill=COR_BLOCO_BG,
        )

        # Label do bloco — linha laranja
        draw.rectangle([(PAD, y), (PAD + 4, y + bloco_h)], fill=COR_ACENTO)
        lbl_x = PAD + 16
        draw.text(
            (lbl_x, y + 8),
            f"BLOCO {bloco.label}",
            font=f_label,
            fill=COR_LABEL,
        )
        y += 28

        # Exercícios
        for ei, ex in enumerate(exercicios):
            nome_lines = wrap_text(ex.nome, f_ex_nome, INNER - PAD_SM * 2, draw)

            # Número do exercício
            num_txt = f"{bloco.label}{ei+1}"
            draw.text((lbl_x, y), num_txt, font=f_label, fill=COR_ACENTO)
            num_w = int(draw.textlength(num_txt, font=f_label)) + 10

            # Nome
            nome_x = lbl_x + num_w
            for li, line in enumerate(nome_lines):
                draw.text(
                    (nome_x, y + li * (text_height(f_ex_nome) + 2)),
                    line,
                    font=f_ex_nome,
                    fill=COR_NOME,
                )
            y += len(nome_lines) * (text_height(f_ex_nome) + 2)

            # Prescrição: séries × reps · RIR X
            partes_prescr = []
            if ex.series:
                partes_prescr.append(f"{ex.series} séries")
            if ex.reps:
                partes_prescr.append(f"{ex.reps} reps")
            if ex.rir is not None:
                partes_prescr.append(f"RIR {ex.rir}")
            if partes_prescr:
                prescr_txt = " · ".join(partes_prescr)
                draw.text((nome_x, y + 2), prescr_txt, font=f_prescr, fill=COR_ACENTO)
                y += text_height(f_prescr) + 4

            y += 10

            # Divisor entre exercícios (não no último)
            if ei < len(exercicios) - 1:
                draw.line(
                    [(lbl_x + 16, y), (PAD + INNER - PAD_SM, y)],
                    fill=COR_DIVISOR,
                    width=1,
                )

        y += 16  # espaço entre blocos

    # --- Rodapé ---
    draw.line([(PAD, y), (PAD + INNER, y)], fill=COR_DIVISOR, width=1)
    draw.text(
        (W // 2, y + 10),
        "gerado por workout app",
        font=f_ex_meta,
        fill=COR_LABEL,
        anchor="mt",
    )

    # Exportar para bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG", dpi=(150, 150))
    buf.seek(0)
    return buf.getvalue()
