"""Transcreve a voz já editada (saída do montar_voz_editada_16k.py) com faster-whisper, com tempo por palavra.

Gera:
  - <saida>.jsonl : um segmento por linha, com as palavras (entrada do montar_srt_editado.py)
  - <saida>.txt   : texto corrido com minutagem, para ler o vídeo final inteiro procurando gagueira,
                    retomada que sobrou ou palavra comida num corte

Não rode junto com o Playwright (o large-v3 ocupa ~5,5 GB de RAM).

Uso: python3 transcrever_voz_editada.py <modelo> <voz_editada_16k.wav> <saida_sem_extensao> ["prompt com nomes próprios do vídeo"]
"""
import json
import subprocess
import sys

import numpy as np
from faster_whisper import WhisperModel

PROMPT_INICIAL = "Olá, pessoal. No vídeo de hoje eu vou mostrar como funciona, passo a passo."


def principal():
    nome_modelo, caminho_audio, prefixo_saida = sys.argv[1:4]
    prompt_inicial = sys.argv[4] if len(sys.argv) > 4 else PROMPT_INICIAL
    modelo = WhisperModel(nome_modelo, device="cpu", compute_type="int8", cpu_threads=2)
    audio = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", caminho_audio, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                                         capture_output=True, check=True).stdout, dtype=np.float32)
    segmentos, _ = modelo.transcribe(audio, language="pt", beam_size=5, vad_filter=False, condition_on_previous_text=False,
                                     initial_prompt=prompt_inicial, word_timestamps=True)
    with open(prefixo_saida + ".jsonl", "w", encoding="utf-8") as arquivo_jsonl, open(prefixo_saida + ".txt", "w", encoding="utf-8") as arquivo_texto:
        for segmento in segmentos:
            palavras = [{"inicio": palavra.start, "fim": palavra.end, "palavra": palavra.word} for palavra in segmento.words]
            arquivo_jsonl.write(json.dumps({"inicio": segmento.start, "fim": segmento.end, "texto": segmento.text, "palavras": palavras}, ensure_ascii=False) + "\n")
            arquivo_texto.write(f"[{segmento.start:7.1f}] {segmento.text.strip()}\n")
            arquivo_jsonl.flush()
            arquivo_texto.flush()
    print("transcrição da voz editada pronta")


if __name__ == "__main__":
    principal()
