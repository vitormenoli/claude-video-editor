"""Monta a voz JÁ EDITADA (só os trechos mantidos, na mesma linha do tempo do vídeo final) em 16 kHz mono.

Serve para a transcrição de conferência (ler o texto final procurando gagueira ou palavra comida) e para
gerar a legenda .srt sem herdar erro de encaixe dos cortes. Roda na nuvem, a partir do voz_16k.flac.

Uso: python3 montar_voz_editada_16k.py <voz_16k.flac> <mapa_tempo.json> <saida.wav>
"""
import json
import subprocess
import sys
import wave

import numpy as np

TAXA = 16000
AMOSTRAS_DE_FADE = 80


def principal():
    caminho_voz, caminho_mapa, caminho_saida = sys.argv[1:4]
    bruto = subprocess.run(["ffmpeg", "-v", "error", "-i", caminho_voz, "-f", "f32le", "-ac", "1", "-ar", str(TAXA), "-"],
                           capture_output=True, check=True).stdout
    amostras = np.frombuffer(bruto, dtype=np.float32)
    mapa = json.load(open(caminho_mapa, encoding="utf-8"))
    pedacos = []
    for trecho in mapa:
        pedaco = amostras[int(trecho["inicio_fonte"] * TAXA):int(trecho["fim_fonte"] * TAXA)].copy()
        tamanho_fade = min(AMOSTRAS_DE_FADE, len(pedaco) // 2)
        if tamanho_fade > 0:
            pedaco[:tamanho_fade] *= np.linspace(0, 1, tamanho_fade)
            pedaco[-tamanho_fade:] *= np.linspace(1, 0, tamanho_fade)
        pedacos.append(pedaco)
    voz_editada = np.clip(np.concatenate(pedacos), -1, 1)
    with wave.open(caminho_saida, "wb") as arquivo:
        arquivo.setnchannels(1)
        arquivo.setsampwidth(2)
        arquivo.setframerate(TAXA)
        arquivo.writeframes((voz_editada * 32767).astype(np.int16).tobytes())
    print(f"voz editada: {len(voz_editada) / TAXA:.2f} s")


if __name__ == "__main__":
    principal()
