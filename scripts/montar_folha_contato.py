"""Folha de contato dos motions: cada motion composto sobre um quadro REAL do bruto no instante em que ele aparece.

Serve para conferir antes do render: texto estourando, elemento cobrindo algo importante da tela, sobreposição.
Usa os PNG da prévia (`node motions/renderizar.js especificacoes_motions.json pasta_previa --previa`).
Motions de layout "dividido" recebem a tela reduzida à direita, como no vídeo final.

Uso: python3 montar_folha_contato.py <plano.json> <mapa_tempo.json> <video_bruto.mp4> <pasta_previa> <prefixo_saida> [indice_do_quadro_da_previa]
Gera <prefixo_saida>_0.jpg, <prefixo_saida>_1.jpg ... com 12 motions por folha (3 colunas x 4 linhas).
"""
import io
import json
import subprocess
import sys

from PIL import Image, ImageDraw

LARGURA_MINIATURA, ALTURA_MINIATURA = 640, 360
COLUNAS, LINHAS = 3, 4
TELA_DIVIDIDA_X, TELA_DIVIDIDA_Y, TELA_DIVIDIDA_LARGURA, TELA_DIVIDIDA_ALTURA = 592, 180, 1280, 720


def saida_para_fonte(tempo_saida, mapa):
    for trecho in mapa:
        duracao_trecho = trecho["fim_fonte"] - trecho["inicio_fonte"]
        if trecho["inicio_saida"] <= tempo_saida < trecho["inicio_saida"] + duracao_trecho:
            return trecho["inicio_fonte"] + (tempo_saida - trecho["inicio_saida"])
    return mapa[-1]["fim_fonte"]


def quadro_do_bruto(caminho_bruto, tempo_fonte):
    bytes_jpg = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{tempo_fonte:.3f}", "-i", caminho_bruto, "-frames:v", "1",
                                "-vf", "scale=1920:1080", "-f", "image2", "-c:v", "mjpeg", "-"], capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(bytes_jpg)).convert("RGBA")


def principal():
    caminho_plano, caminho_mapa, caminho_bruto, pasta_previa, prefixo_saida = sys.argv[1:6]
    indice_padrao = int(sys.argv[6]) if len(sys.argv) > 6 else None
    plano = json.load(open(caminho_plano, encoding="utf-8"))
    mapa = json.load(open(caminho_mapa, encoding="utf-8"))
    miniaturas = []
    for motion in plano["motions"]:
        if motion["tipo"] == "transicao":
            continue
        nome = motion["arquivo"][:-5]
        indice_quadro = indice_padrao if indice_padrao is not None else (4 if motion["tipo"] in ("painel", "numero", "abertura", "comparacao") else 3)
        camada_motion = Image.open(f"{pasta_previa}/{nome}_{indice_quadro}.png").convert("RGBA")
        tempo_fonte = saida_para_fonte(motion["inicio"] + motion["duracao"] * 0.6, mapa)
        fundo = quadro_do_bruto(caminho_bruto, tempo_fonte)
        if motion["modo"] == "dividido":
            composicao = Image.new("RGBA", (1920, 1080))
            composicao.alpha_composite(camada_motion)
            composicao.alpha_composite(fundo.resize((TELA_DIVIDIDA_LARGURA, TELA_DIVIDIDA_ALTURA)), (TELA_DIVIDIDA_X, TELA_DIVIDIDA_Y))
        else:
            composicao = fundo
            composicao.alpha_composite(camada_motion)
        miniatura = composicao.convert("RGB").resize((LARGURA_MINIATURA, ALTURA_MINIATURA))
        desenho = ImageDraw.Draw(miniatura)
        desenho.rectangle((0, 0, 260, 18), fill="black")
        desenho.text((4, 3), f"{nome} {motion['inicio']:.1f}s", fill="yellow")
        miniaturas.append(miniatura)
    por_folha = COLUNAS * LINHAS
    for numero_folha, inicio in enumerate(range(0, len(miniaturas), por_folha)):
        folha = Image.new("RGB", (LARGURA_MINIATURA * COLUNAS, ALTURA_MINIATURA * LINHAS))
        for posicao, miniatura in enumerate(miniaturas[inicio:inicio + por_folha]):
            folha.paste(miniatura, ((posicao % COLUNAS) * LARGURA_MINIATURA, (posicao // COLUNAS) * ALTURA_MINIATURA))
        folha.save(f"{prefixo_saida}_{numero_folha}.jpg", quality=85)
    print(f"{len(miniaturas)} motions em {(len(miniaturas) + por_folha - 1) // por_folha} folhas")


if __name__ == "__main__":
    principal()
