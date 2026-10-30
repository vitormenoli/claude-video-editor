"""Mostra, para cada intervalo do bruto, as rajadas de voz medidas pela energia (onde a fala realmente está)
e as palavras que o Whisper marcou ali. Serve para escolher o ponto exato de um corte manual ("exato": true).

Lembrete: o Whisper costuma marcar as palavras ~0,3 s antes do som real.

Uso: python3 rajadas.py <voz_16k.flac> <transcricao_disfluencias.jsonl> <inicio:fim> [<inicio:fim> ...]
"""
import json
import subprocess
import sys

import numpy as np

LIMIAR_DB = -40.0
JANELA_AMOSTRAS = 160
MINIMO_JANELAS_DE_VOZ = 3


def rajadas_de_voz(caminho_voz, inicio, fim):
    bruto = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(inicio), "-t", str(fim - inicio), "-i", caminho_voz,
                            "-f", "f32le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    amostras = np.frombuffer(bruto, dtype=np.float32)
    quantidade = len(amostras) // JANELA_AMOSTRAS
    energia_db = 20 * np.log10(np.sqrt(np.mean(amostras[:quantidade * JANELA_AMOSTRAS].reshape(quantidade, JANELA_AMOSTRAS) ** 2, axis=1)) + 1e-9)
    tem_voz = energia_db > LIMIAR_DB
    rajadas = []
    indice = 0
    while indice < quantidade:
        if tem_voz[indice]:
            fim_rajada = indice
            while fim_rajada < quantidade and tem_voz[fim_rajada]:
                fim_rajada += 1
            if fim_rajada - indice >= MINIMO_JANELAS_DE_VOZ:
                rajadas.append(f"{inicio + indice * 0.01:.2f}-{inicio + fim_rajada * 0.01:.2f}")
            indice = fim_rajada
        else:
            indice += 1
    return rajadas


def principal():
    caminho_voz, caminho_transcricao = sys.argv[1:3]
    palavras = []
    for linha in open(caminho_transcricao, encoding="utf-8"):
        palavras.extend(json.loads(linha)["palavras"])
    for intervalo in sys.argv[3:]:
        inicio, fim = map(float, intervalo.split(":"))
        print("==", intervalo)
        print(" fala:", " ".join(rajadas_de_voz(caminho_voz, inicio, fim)))
        print(" whisper:", " ".join(f"{palavra['inicio']:.2f}{palavra['palavra']}" for palavra in palavras if inicio <= palavra["inicio"] <= fim))


if __name__ == "__main__":
    principal()
