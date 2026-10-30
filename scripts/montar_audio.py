"""Monta o áudio final do vídeo editado, em etapas curtas (cada uma cabe no limite de tempo de um comando).

Etapas:
  cortar     corta a voz do bruto nos trechos mantidos (micro-fades de 4 ms em cada emenda) -> voz_cortada.wav
  medir      1ª passada do loudnorm (só medição)
  tratar     filtro passa-alta, redução leve de ruído, compressão leve e loudnorm em 2 passadas (-14 LUFS, -1,5 dBTP) -> voz_tratada.wav
  mixar      música em loop (fade in 1 s, ducking quando há voz, fade out 1,5 s terminando na entrada do encerramento),
             efeitos sonoros dos motions bem baixos e o áudio original do encerramento no fim -> mix_final.wav
  codificar  AAC 192 kbps -> audio_final.m4a

Uso: python3 montar_audio.py <plano.json> <etapa>
"""
import json
import os
import subprocess
import sys
import wave

import numpy as np

TAXA = 48000


def ler_wav(caminho):
    with wave.open(caminho, "rb") as arquivo:
        canais = arquivo.getnchannels()
        dados = np.frombuffer(arquivo.readframes(arquivo.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    return dados.reshape(-1, canais)


def gravar_wav(caminho, amostras):
    if amostras.ndim == 1:
        amostras = amostras[:, None]
    inteiros = (np.clip(amostras, -1.0, 1.0) * 32767.0).astype(np.int16)
    with wave.open(caminho, "wb") as arquivo:
        arquivo.setnchannels(amostras.shape[1])
        arquivo.setsampwidth(2)
        arquivo.setframerate(TAXA)
        arquivo.writeframes(inteiros.tobytes())


def decodificar_com_ffmpeg(caminho, canais):
    saida = subprocess.run(["ffmpeg", "-v", "error", "-i", caminho, "-ac", str(canais), "-ar", str(TAXA), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(saida, dtype=np.float32).reshape(-1, canais).copy()


def decibeis_para_ganho(valor_db):
    return 10.0 ** (valor_db / 20.0)


def etapa_cortar(plano, pasta):
    voz_bruta = ler_wav(plano["voz_bruta_48k"])[:, 0]
    tamanho_fade = int(0.004 * TAXA)
    rampa_entrada = np.linspace(0.0, 1.0, tamanho_fade, dtype=np.float32)
    pedacos = []
    for inicio_fonte, fim_fonte in plano["trechos"]:
        inicio_amostra = int(round(inicio_fonte * TAXA))
        fim_amostra = int(round(fim_fonte * TAXA))
        pedaco = voz_bruta[inicio_amostra:fim_amostra].copy()
        if len(pedaco) < fim_amostra - inicio_amostra:
            pedaco = np.concatenate([pedaco, np.zeros(fim_amostra - inicio_amostra - len(pedaco), dtype=np.float32)])
        if len(pedaco) > 2 * tamanho_fade:
            pedaco[:tamanho_fade] *= rampa_entrada
            pedaco[-tamanho_fade:] *= rampa_entrada[::-1]
        pedacos.append(pedaco)
    voz_cortada = np.concatenate(pedacos)
    gravar_wav(os.path.join(pasta, "voz_cortada.wav"), voz_cortada)
    print(f"voz cortada: {len(voz_cortada) / TAXA:.2f} s")


CADEIA_BASE_VOZ = "highpass=f=70,afftdn=nr=8:nf=-55,acompressor=threshold=-22dB:ratio=2.5:attack=8:release=160:makeup=1"


def etapa_medir(plano, pasta):
    """1ª passada do loudnorm (só mede); as medidas ficam salvas para a 2ª passada."""
    caminho_entrada = os.path.join(pasta, "voz_cortada.wav")
    medicao = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", caminho_entrada, "-af", CADEIA_BASE_VOZ + ",loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
    medidas = json.loads(medicao[medicao.rfind("{"):medicao.rfind("}") + 1])
    json.dump(medidas, open(os.path.join(pasta, "medidas_loudnorm.json"), "w"))
    print("medidas da 1ª passada:", medidas["input_i"], "LUFS")


def etapa_tratar(plano, pasta):
    """2ª passada: aplica a cadeia de voz com o loudnorm linear usando as medidas salvas."""
    caminho_entrada = os.path.join(pasta, "voz_cortada.wav")
    medidas = json.load(open(os.path.join(pasta, "medidas_loudnorm.json")))
    segunda_passada = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={medidas['input_i']}:measured_TP={medidas['input_tp']}:"
                       f"measured_LRA={medidas['input_lra']}:measured_thresh={medidas['input_thresh']}:offset={medidas['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", caminho_entrada, "-af", CADEIA_BASE_VOZ + "," + segunda_passada + ",aresample=48000",
                    "-ar", "48000", "-c:a", "pcm_s16le", os.path.join(pasta, "voz_tratada.wav")], check=True)
    print("voz tratada")


def envelope_de_voz(voz_mono):
    """Envelope de ducking: 1 onde não há fala, ganho reduzido onde há fala, com ataque e soltura suaves."""
    tamanho_janela = int(0.02 * TAXA)
    quantidade_janelas = len(voz_mono) // tamanho_janela
    energia = np.sqrt(np.mean(voz_mono[:quantidade_janelas * tamanho_janela].reshape(quantidade_janelas, tamanho_janela) ** 2, axis=1) + 1e-12)
    tem_voz = 20 * np.log10(energia) > -38.0
    alvo = np.where(tem_voz, 1.0, 0.0)
    suavizado = np.zeros_like(alvo)
    valor = 0.0
    coeficiente_ataque = np.exp(-0.02 / 0.08)
    coeficiente_soltura = np.exp(-0.02 / 0.45)
    for indice, objetivo in enumerate(alvo):
        coeficiente = coeficiente_ataque if objetivo > valor else coeficiente_soltura
        valor = coeficiente * valor + (1 - coeficiente) * objetivo
        suavizado[indice] = valor
    por_amostra = np.repeat(suavizado, tamanho_janela)
    if len(por_amostra) < len(voz_mono):
        por_amostra = np.concatenate([por_amostra, np.full(len(voz_mono) - len(por_amostra), por_amostra[-1] if len(por_amostra) else 0.0)])
    return por_amostra.astype(np.float32)


def musica_em_loop(musica, tamanho_total):
    sobreposicao = int(1.5 * TAXA)
    resultado = np.zeros((tamanho_total, 2), dtype=np.float32)
    rampa = np.linspace(0.0, 1.0, sobreposicao, dtype=np.float32)[:, None]
    posicao = 0
    primeira_vez = True
    while posicao < tamanho_total:
        pedaco = musica.copy()
        if not primeira_vez:
            pedaco[:sobreposicao] *= rampa
        pedaco[-sobreposicao:] *= rampa[::-1]
        fim = min(tamanho_total, posicao + len(pedaco))
        resultado[posicao:fim] += pedaco[:fim - posicao]
        posicao += len(pedaco) - sobreposicao
        primeira_vez = False
    return resultado


def etapa_mixar(plano, pasta):
    voz = ler_wav(os.path.join(pasta, "voz_tratada.wav"))[:, 0]
    duracao_crossfade = plano.get("crossfade_final", 0.0)
    amostras_video = int(round(plano["fim_video"] * TAXA))
    amostras_ate_encerramento = int(round((plano["fim_video"] - duracao_crossfade) * TAXA))
    if len(voz) < amostras_video:
        voz = np.concatenate([voz, np.zeros(amostras_video - len(voz), dtype=np.float32)])
    voz = voz[:amostras_video]

    musica = decodificar_com_ffmpeg(plano["musica"], 2)
    trilha = musica_em_loop(musica, amostras_video)
    ganho_base = decibeis_para_ganho(plano["musica_alvo_lufs"] - plano["musica_lufs_original"])
    reducao_com_voz = decibeis_para_ganho(plano["ducking_db"])
    envelope = envelope_de_voz(voz)
    ganho_trilha = ganho_base * (1.0 - envelope * (1.0 - reducao_com_voz))
    amostras_fade_entrada = int(1.0 * TAXA)
    amostras_fade_saida = int(1.5 * TAXA)
    ganho_trilha[:amostras_fade_entrada] *= np.linspace(0.0, 1.0, amostras_fade_entrada, dtype=np.float32)
    # A música some em 1,5 s e termina exatamente quando o encerramento começa a entrar (início do crossfade).
    ganho_trilha[amostras_ate_encerramento - amostras_fade_saida:amostras_ate_encerramento] *= np.linspace(1.0, 0.0, amostras_fade_saida, dtype=np.float32)
    ganho_trilha[amostras_ate_encerramento:] = 0.0
    trilha *= ganho_trilha[:, None]

    efeitos = np.zeros((amostras_video, 2), dtype=np.float32)
    cache_efeitos = {}
    for efeito in plano.get("efeitos_sonoros", []):
        caminho_efeito = os.path.join(plano["pasta_trabalho"], "sons", efeito["arquivo"])
        if caminho_efeito not in cache_efeitos:
            cache_efeitos[caminho_efeito] = ler_wav(caminho_efeito)
        amostras_efeito = cache_efeitos[caminho_efeito] * decibeis_para_ganho(efeito.get("ganho_db", plano["efeitos_ganho_db"]))
        inicio = int(round(efeito["tempo"] * TAXA))
        fim = min(amostras_video, inicio + len(amostras_efeito))
        if inicio < amostras_video:
            efeitos[inicio:fim] += amostras_efeito[:fim - inicio]

    # A voz foi normalizada em mono (-14 LUFS); copiada nos dois canais ela soma +3 dB, então desconta 3 dB.
    voz_estereo = np.repeat(voz[:, None], 2, axis=1) * decibeis_para_ganho(-3.01)
    mistura_video = voz_estereo + trilha + efeitos
    audio_encerramento = decodificar_com_ffmpeg(plano["encerramento"], 2)
    amostras_encerramento = int(round(plano["duracao_encerramento"] * TAXA))
    if len(audio_encerramento) < amostras_encerramento:
        audio_encerramento = np.concatenate([audio_encerramento, np.zeros((amostras_encerramento - len(audio_encerramento), 2), dtype=np.float32)])
    # O encerramento entra no início do crossfade, com o áudio original dele sem mudança de volume.
    mistura_total = np.zeros((amostras_ate_encerramento + amostras_encerramento, 2), dtype=np.float32)
    mistura_total[:amostras_video] += mistura_video
    mistura_total[amostras_ate_encerramento:amostras_ate_encerramento + amostras_encerramento] += audio_encerramento[:amostras_encerramento]
    pico = float(np.max(np.abs(mistura_total)))
    if pico > 0.89:
        mistura_total *= 0.89 / pico
    gravar_wav(os.path.join(pasta, "mix_final.wav"), mistura_total)
    print(f"mix final: {len(mistura_total) / TAXA:.2f} s, pico {20 * np.log10(max(pico, 1e-9)):.1f} dBFS")


def etapa_codificar(plano, pasta):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(pasta, "mix_final.wav"), "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    os.path.join(pasta, "audio_final.m4a")], check=True)
    print("audio_final.m4a pronto")


if __name__ == "__main__":
    plano_carregado = json.load(open(sys.argv[1], encoding="utf-8"))
    pasta_audio = os.path.join(plano_carregado["pasta_trabalho"], "audio")
    os.makedirs(pasta_audio, exist_ok=True)
    etapas = {"cortar": etapa_cortar, "medir": etapa_medir, "tratar": etapa_tratar, "mixar": etapa_mixar, "codificar": etapa_codificar}
    etapas[sys.argv[2]](plano_carregado, pasta_audio)
