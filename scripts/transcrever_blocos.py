"""Transcreve o áudio em blocos (cortados em silêncios) para não estourar a memória.
Uso: python3 transcrever_blocos.py <modelo> <audio> <saida.jsonl> <arquivo_blocos>"""
import json
import subprocess
import sys
import time

import numpy as np
from faster_whisper import WhisperModel

nome_modelo, caminho_audio, caminho_saida, caminho_blocos = sys.argv[1:5]
primeiro_bloco = int(sys.argv[5]) if len(sys.argv) > 5 else 0
limites_blocos = [float(valor) for valor in open(caminho_blocos).read().split()]
inicio_relogio = time.time()
modelo = WhisperModel(nome_modelo, device="cpu", compute_type="int8", cpu_threads=2)

with open(caminho_saida, "a" if primeiro_bloco > 0 else "w", encoding="utf-8") as arquivo_saida:
    for indice_bloco in range(primeiro_bloco, len(limites_blocos) - 1):
        inicio_bloco = limites_blocos[indice_bloco]
        duracao_bloco = limites_blocos[indice_bloco + 1] - inicio_bloco
        comando_ffmpeg = ["ffmpeg", "-v", "error", "-ss", str(inicio_bloco), "-t", str(duracao_bloco), "-i", caminho_audio,
                          "-ac", "1", "-ar", "16000", "-f", "f32le", "-"]
        audio_bloco = np.frombuffer(subprocess.run(comando_ffmpeg, capture_output=True, check=True).stdout, dtype=np.float32)
        segmentos, _ = modelo.transcribe(audio_bloco, language="pt", word_timestamps=True, beam_size=5,
                                         vad_filter=True, vad_parameters={"min_silence_duration_ms": 500},
                                         condition_on_previous_text=False)
        for segmento in segmentos:
            palavras = [{"inicio": round(palavra.start + inicio_bloco, 3), "fim": round(palavra.end + inicio_bloco, 3),
                         "palavra": palavra.word, "prob": round(palavra.probability, 3)} for palavra in (segmento.words or [])]
            registro = {"inicio": round(segmento.start + inicio_bloco, 3), "fim": round(segmento.end + inicio_bloco, 3),
                        "texto": segmento.text, "palavras": palavras}
            arquivo_saida.write(json.dumps(registro, ensure_ascii=False) + "\n")
            arquivo_saida.flush()
        print(f"bloco {indice_bloco + 1}/{len(limites_blocos) - 1} pronto em {round(time.time() - inicio_relogio)}s", flush=True)
print("concluido em", round(time.time() - inicio_relogio), "s", flush=True)
