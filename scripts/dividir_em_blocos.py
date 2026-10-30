"""Escolhe os limites dos blocos de transcrição (~8 min cada), sempre no meio de um silêncio,
para o transcrever_blocos.py não cortar nenhuma palavra ao meio e não estourar a memória.

Uso: python3 dividir_em_blocos.py <silencios_ffmpeg.txt> <duracao_do_bruto_s> <saida_blocos.txt> [tamanho_alvo_s]
O silencios_ffmpeg.txt vem de: ffmpeg -i voz_16k.flac -af silencedetect=noise=-40dB:d=0.3 -f null - 2> silencios_03.txt
"""
import re
import sys

TAMANHO_ALVO_PADRAO = 480.0


def ler_silencios(caminho):
    texto = open(caminho, encoding="utf-8", errors="ignore").read()
    inicios = [float(valor) for valor in re.findall(r"silence_start: ([\d.]+)", texto)]
    fins = [float(valor) for valor in re.findall(r"silence_end: ([\d.]+)", texto)]
    return list(zip(inicios, fins))


def principal():
    caminho_silencios, duracao_bruto, caminho_saida = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    tamanho_alvo = float(sys.argv[4]) if len(sys.argv) > 4 else TAMANHO_ALVO_PADRAO
    meios_dos_silencios = [(inicio + fim) / 2 for inicio, fim in ler_silencios(caminho_silencios)]
    limites = [0.0]
    while duracao_bruto - limites[-1] > tamanho_alvo * 1.25:
        alvo = limites[-1] + tamanho_alvo
        candidatos = [meio for meio in meios_dos_silencios if limites[-1] + tamanho_alvo * 0.6 < meio < limites[-1] + tamanho_alvo * 1.2]
        limites.append(min(candidatos, key=lambda meio: abs(meio - alvo)) if candidatos else alvo)
    limites.append(duracao_bruto)
    open(caminho_saida, "w").write(" ".join(f"{limite:.2f}" for limite in limites) + "\n")
    print("blocos:", " ".join(f"{limite:.2f}" for limite in limites))


if __name__ == "__main__":
    principal()
