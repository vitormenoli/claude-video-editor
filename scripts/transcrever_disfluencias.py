"""Segunda passada de transcrição feita para PEGAR gagueira: o Whisper normalmente "limpa" repetições
("o o", "aí aí", "tipo tipo") e falsos começos. Aqui cada janela de fala (~25 s, cortada em silêncios)
é transcrita com um prompt cheio de hesitações, o que faz o modelo escrever o que foi falado literalmente.

Uso: python3 transcrever_disfluencias.py <modelo> <audio_16k> <silencios_ffmpeg.txt> <saida.jsonl> [inicio] [fim]
"""
import json
import re
import subprocess
import sys
import time

import numpy as np
from faster_whisper import WhisperModel

PROMPT_COM_HESITACOES = ("Ééé... então, tipo, tipo assim, a a gente vai, vai fazer o o setup, né, né? Aí, aí ele, ele... "
                         "Hum, eu eu vou, vou mostrar. É... é bem, bem simples, tá? Pra pra gente, a gente, a gente instalar.")
TAMANHO_JANELA_ALVO = 25.0
TAXA = 16000


def carregar_silencios(caminho):
    silencios = []
    for linha in open(caminho):
        correspondencia = re.search(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", linha)
        if correspondencia:
            fim = float(correspondencia.group(1))
            silencios.append((fim - float(correspondencia.group(2)), fim))
    return silencios


def montar_janelas(silencios, inicio_total, fim_total):
    """Janelas de ~25 s terminando no meio de um silêncio, para nenhuma palavra ser cortada ao meio."""
    janelas = []
    inicio_janela = inicio_total
    pontos_de_corte = [(inicio + fim) / 2 for inicio, fim in silencios if fim - inicio >= 0.4]
    while inicio_janela < fim_total - 0.5:
        candidatos = [ponto for ponto in pontos_de_corte if inicio_janela + 12 < ponto < inicio_janela + 30]
        if candidatos:
            fim_janela = min(candidatos, key=lambda ponto: abs(ponto - (inicio_janela + TAMANHO_JANELA_ALVO)))
        else:
            fim_janela = min(fim_total, inicio_janela + 30)
        janelas.append((inicio_janela, min(fim_janela, fim_total)))
        inicio_janela = fim_janela
    return janelas


def principal():
    nome_modelo, caminho_audio, caminho_silencios, caminho_saida = sys.argv[1:5]
    inicio_total = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
    audio_completo = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", caminho_audio, "-ac", "1", "-ar", str(TAXA), "-f", "f32le", "-"],
                                                  capture_output=True, check=True).stdout, dtype=np.float32)
    fim_total = float(sys.argv[6]) if len(sys.argv) > 6 else len(audio_completo) / TAXA
    silencios = carregar_silencios(caminho_silencios)
    janelas = montar_janelas(silencios, inicio_total, fim_total)
    modelo = WhisperModel(nome_modelo, device="cpu", compute_type="int8", cpu_threads=2)
    inicio_relogio = time.time()
    with open(caminho_saida, "a" if inicio_total > 0 else "w", encoding="utf-8") as arquivo_saida:
        for indice, (inicio_janela, fim_janela) in enumerate(janelas):
            trecho = audio_completo[int(inicio_janela * TAXA):int(fim_janela * TAXA)]
            energia = float(np.sqrt(np.mean(trecho ** 2))) if len(trecho) else 0.0
            if energia < 10 ** (-50 / 20):
                continue
            segmentos, _ = modelo.transcribe(trecho, language="pt", word_timestamps=True, beam_size=5, initial_prompt=PROMPT_COM_HESITACOES,
                                             vad_filter=True, vad_parameters={"min_silence_duration_ms": 300}, condition_on_previous_text=False,
                                             suppress_blank=False)
            for segmento in segmentos:
                palavras = [{"inicio": round(palavra.start + inicio_janela, 3), "fim": round(palavra.end + inicio_janela, 3),
                             "palavra": palavra.word, "prob": round(palavra.probability, 3)} for palavra in (segmento.words or [])]
                arquivo_saida.write(json.dumps({"inicio": round(segmento.start + inicio_janela, 3), "fim": round(segmento.end + inicio_janela, 3),
                                                "texto": segmento.text, "palavras": palavras}, ensure_ascii=False) + "\n")
                arquivo_saida.flush()
            if indice % 10 == 0:
                print(f"janela {indice + 1}/{len(janelas)} ({fim_janela:.0f}s) em {round(time.time() - inicio_relogio)}s", flush=True)
    print("concluido em", round(time.time() - inicio_relogio), "s", flush=True)


if __name__ == "__main__":
    principal()
