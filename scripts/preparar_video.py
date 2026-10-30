"""Prepara um vídeo novo a partir da pasta "Arquivos Brutos": acha o bruto e o roteiro, junta as partes,
extrai os áudios e gera os arquivos de partida da edição dentro de "_edicao".

Regras da pasta "Arquivos Brutos":
  - um vídeo só (qualquer nome), OU vários nomeados em ordem: "Parte 1.mp4", "Parte 2.mp4"...;
  - um roteiro em .md ou .txt (se houver mais de um, o que tiver "roteiro" no nome).

Gera em _edicao/:
  bruto.mp4 (só quando há partes: as partes juntadas na ordem)
  voz_16k.flac, voz_48k.wav, silencios_03.txt, blocos.txt
  roteiro.md                 cópia do roteiro
  configuracao_video.json    caminhos e volumes usados pelo planejar.py, montar_audio.py e renderizar_parte.py
  decisoes.json              ponto de partida dos cortes manuais (não sobrescreve um que já exista)

Uso: python3 preparar_video.py <pasta_de_edicao> [--refazer]
  --refazer: extrai os áudios de novo mesmo que já existam.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dividir_em_blocos import ler_silencios  # noqa: E402

PASTA_DA_SKILL = Path(__file__).resolve().parent.parent
EXTENSOES_DE_VIDEO = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
EXTENSOES_DE_ROTEIRO = {".md", ".txt"}
PADRAO_PARTE = re.compile(r"^parte\s*[_-]?\s*(\d+)$", re.IGNORECASE)
TAMANHO_ALVO_BLOCO = 480.0


class ErroDaPasta(Exception):
    pass


def ffprobe_json(caminho):
    saida = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
                            "-of", "json", str(caminho)], capture_output=True, text=True, check=True).stdout
    return json.loads(saida)


def duracao_do_arquivo(caminho):
    return float(ffprobe_json(caminho)["format"]["duration"])


def assinatura_tecnica(caminho):
    """Codec, resolução, fps e áudio: partes iguais podem ser juntadas sem recompressão."""
    fluxos = ffprobe_json(caminho)["streams"]
    video = next((fluxo for fluxo in fluxos if fluxo["codec_type"] == "video"), {})
    audio = next((fluxo for fluxo in fluxos if fluxo["codec_type"] == "audio"), {})
    return (video.get("codec_name"), video.get("width"), video.get("height"), video.get("r_frame_rate"),
            audio.get("codec_name"), audio.get("sample_rate"), audio.get("channels"))


def achar_videos(pasta_brutos):
    videos = sorted(arquivo for arquivo in pasta_brutos.iterdir() if arquivo.is_file() and arquivo.suffix.lower() in EXTENSOES_DE_VIDEO)
    if not videos:
        raise ErroDaPasta(f'Nenhum vídeo em "{pasta_brutos}". Coloque o bruto lá (um vídeo só, ou "Parte 1.mp4", "Parte 2.mp4"...).')
    if len(videos) == 1:
        return videos
    numerados = []
    fora_do_padrao = []
    for video in videos:
        correspondencia = PADRAO_PARTE.match(video.stem.strip())
        if correspondencia:
            numerados.append((int(correspondencia.group(1)), video))
        else:
            fora_do_padrao.append(video.name)
    if fora_do_padrao:
        raise ErroDaPasta("Há mais de um vídeo e estes não seguem o padrão \"Parte N\": " + ", ".join(fora_do_padrao)
                          + '. Deixe um vídeo só, ou renomeie todos como "Parte 1.mp4", "Parte 2.mp4"...')
    numeros = [numero for numero, _ in numerados]
    if len(set(numeros)) != len(numeros):
        raise ErroDaPasta("Há duas partes com o mesmo número: " + ", ".join(video.name for _, video in numerados))
    numerados.sort()
    esperados = list(range(numerados[0][0], numerados[0][0] + len(numerados)))
    if numeros != esperados and sorted(numeros) != esperados:
        print(f"AVISO: a numeração das partes pula números ({sorted(numeros)}). Vou juntar na ordem dos números.")
    return [video for _, video in numerados]


def achar_roteiro(pasta_brutos):
    candidatos = [arquivo for arquivo in pasta_brutos.iterdir()
                  if arquivo.is_file() and arquivo.suffix.lower() in EXTENSOES_DE_ROTEIRO and not arquivo.stem.upper().startswith("LEIA-ME")]
    if not candidatos:
        return None
    if len(candidatos) == 1:
        return candidatos[0]
    com_nome_de_roteiro = [arquivo for arquivo in candidatos if "roteiro" in arquivo.stem.lower()]
    if len(com_nome_de_roteiro) == 1:
        return com_nome_de_roteiro[0]
    raise ErroDaPasta("Achei mais de um arquivo de texto: " + ", ".join(arquivo.name for arquivo in candidatos)
                      + '. Deixe só o roteiro, ou coloque "roteiro" no nome dele.')


def juntar_partes(partes, caminho_saida):
    assinaturas = {assinatura_tecnica(parte) for parte in partes}
    if len(assinaturas) == 1:
        caminho_lista = caminho_saida.with_suffix(".txt")
        with open(caminho_lista, "w", encoding="utf-8") as arquivo_lista:
            for parte in partes:
                caminho_normalizado = str(parte).replace("\\", "/").replace("'", "'\\''")
                arquivo_lista.write(f"file '{caminho_normalizado}'\n")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(caminho_lista), "-c", "copy", str(caminho_saida)], check=True)
        print(f"partes juntadas sem recompressão: {len(partes)}")
        return
    # Partes com resolução/fps/codec diferentes: normaliza tudo para 1920x1080 30 fps antes de juntar.
    entradas = []
    filtros = []
    for indice, parte in enumerate(partes):
        entradas += ["-i", str(parte)]
        filtros.append(f"[{indice}:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,setsar=1,format=yuv420p[v{indice}];"
                       f"[{indice}:a]aresample=48000,aformat=channel_layouts=stereo[a{indice}]")
    filtros.append("".join(f"[v{indice}][a{indice}]" for indice in range(len(partes))) + f"concat=n={len(partes)}:v=1:a=1[video][audio]")
    subprocess.run(["ffmpeg", "-y", "-v", "error"] + entradas + ["-filter_complex", ";".join(filtros), "-map", "[video]", "-map", "[audio]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-c:a", "aac", "-b:a", "256k", str(caminho_saida)], check=True)
    print(f"partes juntadas com recompressão (eram diferentes entre si): {len(partes)}")


def medir_loudness(caminho):
    saida = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(caminho), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    medidas = re.findall(r"I:\s+(-?[\d.]+) LUFS", saida)
    return float(medidas[-1]) if medidas else -14.0


def escolher_limites_de_blocos(caminho_silencios, duracao_bruto):
    meios_dos_silencios = [(inicio + fim) / 2 for inicio, fim in ler_silencios(str(caminho_silencios))]
    limites = [0.0]
    while duracao_bruto - limites[-1] > TAMANHO_ALVO_BLOCO * 1.25:
        alvo = limites[-1] + TAMANHO_ALVO_BLOCO
        candidatos = [meio for meio in meios_dos_silencios if limites[-1] + TAMANHO_ALVO_BLOCO * 0.6 < meio < limites[-1] + TAMANHO_ALVO_BLOCO * 1.2]
        limites.append(min(candidatos, key=lambda meio: abs(meio - alvo)) if candidatos else alvo)
    limites.append(duracao_bruto)
    return limites


def resolver_midia(pasta_edicao, valor_configurado, descricao):
    if not valor_configurado:
        print(f"{descricao}: desligado na configuração")
        return None
    caminho = Path(valor_configurado)
    caminho = caminho if caminho.is_absolute() else pasta_edicao / caminho
    if not caminho.exists():
        print(f"AVISO: {descricao} não encontrado em \"{caminho}\". O vídeo sai sem ele (coloque o arquivo e rode de novo para incluir).")
        return None
    return caminho


def principal():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    pasta_edicao = Path(sys.argv[1]).expanduser().resolve()
    refazer = "--refazer" in sys.argv
    caminho_configuracao = pasta_edicao / "config_editor.json"
    if not caminho_configuracao.exists():
        print(f"ERRO: não achei {caminho_configuracao}. Rode primeiro o configurar_pasta.py nessa pasta.")
        sys.exit(1)
    configuracao = json.load(open(caminho_configuracao, encoding="utf-8"))
    pasta_brutos = pasta_edicao / "Arquivos Brutos"
    pasta_trabalho = pasta_edicao / "_edicao"
    pasta_trabalho.mkdir(exist_ok=True)

    try:
        videos = achar_videos(pasta_brutos)
        roteiro = achar_roteiro(pasta_brutos)
    except ErroDaPasta as erro:
        print("ERRO:", erro)
        sys.exit(1)

    if len(videos) == 1:
        caminho_bruto = videos[0]
        nome_base = videos[0].stem
    else:
        caminho_bruto = pasta_trabalho / "bruto.mp4"
        nome_base = "Video"
        if refazer or not caminho_bruto.exists():
            juntar_partes(videos, caminho_bruto)
    duracao_bruto = duracao_do_arquivo(caminho_bruto)
    print(f"bruto: {caminho_bruto} ({duracao_bruto / 60:.1f} min)" + (f", juntado de {len(videos)} partes" if len(videos) > 1 else ""))

    caminho_voz_16k = pasta_trabalho / "voz_16k.flac"
    caminho_voz_48k = pasta_trabalho / "voz_48k.wav"
    caminho_silencios = pasta_trabalho / "silencios_03.txt"
    if refazer or not caminho_voz_16k.exists():
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(caminho_bruto), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "flac", str(caminho_voz_16k)], check=True)
    if refazer or not caminho_voz_48k.exists():
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(caminho_bruto), "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(caminho_voz_48k)], check=True)
    if refazer or not caminho_silencios.exists():
        saida_silencios = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(caminho_voz_16k), "-af", "silencedetect=noise=-40dB:d=0.3", "-f", "null", "-"],
                                         capture_output=True, text=True).stderr
        caminho_silencios.write_text(saida_silencios, encoding="utf-8")
    limites = escolher_limites_de_blocos(caminho_silencios, duracao_bruto)
    (pasta_trabalho / "blocos.txt").write_text(" ".join(f"{limite:.2f}" for limite in limites) + "\n", encoding="utf-8")

    if roteiro:
        shutil.copy(roteiro, pasta_trabalho / "roteiro.md")
        print(f"roteiro: {roteiro.name}")
    else:
        print("AVISO: nenhum roteiro (.md ou .txt) em Arquivos Brutos. Os capítulos vão sair da própria fala.")

    caminho_musica = resolver_midia(pasta_edicao, configuracao.get("musica_de_fundo"), "música de fundo")
    caminho_encerramento = resolver_midia(pasta_edicao, configuracao.get("encerramento"), "encerramento")
    configuracao_video = {
        "pasta_trabalho": str(pasta_trabalho),
        "video_bruto": str(caminho_bruto),
        "voz_bruta_48k": str(caminho_voz_48k),
        "nome_saida": f"{nome_base}_editado",
        "pasta_resultado": str(pasta_edicao / "Resultado Final"),
        "pasta_sons": str(PASTA_DA_SKILL / "motions" / "sons"),
        "voz_alvo_lufs": configuracao.get("voz_alvo_lufs", -14.0),
        "voz_pico_dbtp": configuracao.get("voz_pico_dbtp", -1.5),
        "musica": str(caminho_musica) if caminho_musica else None,
        "musica_lufs_original": medir_loudness(caminho_musica) if caminho_musica else None,
        "musica_alvo_lufs": configuracao.get("musica_alvo_lufs", -40.0),
        "ducking_db": configuracao.get("ducking_db", -8.0),
        "usar_efeitos_sonoros": configuracao.get("efeitos_sonoros", True),
        "efeitos_ganho_db": configuracao.get("efeitos_ganho_db", -24.0),
        "encerramento": str(caminho_encerramento) if caminho_encerramento else None,
        "duracao_encerramento": round(duracao_do_arquivo(caminho_encerramento), 6) if caminho_encerramento else 0.0,
        "crossfade_final": configuracao.get("crossfade_final_s", 0.5) if caminho_encerramento else 0.0,
    }
    (pasta_trabalho / "configuracao_video.json").write_text(json.dumps(configuracao_video, ensure_ascii=False, indent=1), encoding="utf-8")

    caminho_decisoes = pasta_trabalho / "decisoes.json"
    if not caminho_decisoes.exists():
        decisoes_iniciais = {"duracao_bruto": round(duracao_bruto, 3), "silencio_minimo_s": configuracao.get("silencio_minimo_s", 0.45),
                             "respiro_s": configuracao.get("respiro_s", 0.08), "remover": [], "manter": [], "correcoes_texto": []}
        caminho_decisoes.write_text(json.dumps(decisoes_iniciais, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"blocos de transcrição: {' '.join(f'{limite:.0f}' for limite in limites)}")
    print(f"música: {caminho_musica.name if caminho_musica else 'sem música'}  ·  encerramento: {caminho_encerramento.name if caminho_encerramento else 'sem encerramento'}")
    print(f"pronto: {pasta_trabalho}")


if __name__ == "__main__":
    principal()
