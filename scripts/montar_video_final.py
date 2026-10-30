"""Monta o áudio, renderiza as partes e junta o vídeo, tudo de uma vez (para quando o computador não tem limite de
tempo por comando, como no Claude Code). Partes que não mudaram desde o último render são reaproveitadas.

Uso:
  python3 montar_video_final.py <pasta_de_edicao> --previas   # só as prévias (primeiros N s e últimos N s) em "Resultado Final/Previas"
  python3 montar_video_final.py <pasta_de_edicao> --final     # vídeo completo em "Resultado Final", com conferência no fim
  Opcional: --refazer-partes (renderiza todas as partes de novo)

Precisa do _edicao/plano.json (gerado pelo planejar.py) e dos motions em _edicao/motions/.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PASTA_DOS_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(PASTA_DOS_SCRIPTS))
import renderizar_parte  # noqa: E402

QUADROS_POR_SEGUNDO = 30


def rodar_script(nome_script, *argumentos):
    comando = [sys.executable, str(PASTA_DOS_SCRIPTS / nome_script)] + [str(argumento) for argumento in argumentos]
    resultado = subprocess.run(comando)
    if resultado.returncode != 0:
        print(f"ERRO em {nome_script} {' '.join(str(argumento) for argumento in argumentos)}")
        sys.exit(resultado.returncode)


def quadros_do_video(caminho):
    saida = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-count_packets", "-show_entries", "stream=nb_read_packets",
                            "-of", "csv=p=0", str(caminho)], capture_output=True, text=True).stdout.strip()
    return int(saida) if saida.isdigit() else -1


def parte_precisa_renderizar(plano, indice_parte, refazer_todas):
    pasta_partes = os.path.join(plano["pasta_trabalho"], "partes")
    caminho_parte = os.path.join(pasta_partes, f"parte_{indice_parte:03d}.mp4")
    caminho_filtro = os.path.join(pasta_partes, f"filtro_{indice_parte:03d}.txt")
    filtro_anterior = open(caminho_filtro, encoding="utf-8").read() if os.path.exists(caminho_filtro) else None
    renderizar_parte.montar_comando(plano, indice_parte)
    filtro_novo = open(caminho_filtro, encoding="utf-8").read()
    if refazer_todas or not os.path.exists(caminho_parte) or filtro_anterior != filtro_novo:
        return True
    inicio_parte, fim_parte = plano["partes"][indice_parte]
    if quadros_do_video(caminho_parte) != round((fim_parte - inicio_parte) * QUADROS_POR_SEGUNDO):
        return True
    momento_da_parte = os.path.getmtime(caminho_parte)
    for motion in plano["motions"]:
        if motion["inicio"] < fim_parte and motion["inicio"] + motion["duracao"] > inicio_parte:
            caminho_motion = os.path.join(plano["pasta_trabalho"], "motions", motion["arquivo"])
            if os.path.exists(caminho_motion) and os.path.getmtime(caminho_motion) > momento_da_parte:
                return True
    return False


def renderizar_partes(caminho_plano, plano, indices, refazer_todas):
    for indice_parte in indices:
        if parte_precisa_renderizar(plano, indice_parte, refazer_todas):
            print(f"renderizando parte {indice_parte + 1}/{len(plano['partes'])}")
            rodar_script("renderizar_parte.py", caminho_plano, indice_parte)
        else:
            print(f"parte {indice_parte + 1}/{len(plano['partes'])} sem mudança")


def montar_audio(caminho_plano):
    for etapa in ("cortar", "medir", "tratar", "mixar", "codificar"):
        rodar_script("montar_audio.py", caminho_plano, etapa)


def conferir_video(caminho_video, plano):
    informacoes = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate,duration",
                                  "-of", "compact", str(caminho_video)], capture_output=True, text=True).stdout.strip()
    loudness = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(caminho_video), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                              capture_output=True, text=True).stderr
    linhas_loudness = [linha.strip() for linha in loudness.splitlines() if linha.strip().startswith(("I:", "Peak:"))][-2:]
    duracao_esperada = plano["fim_video"] - plano.get("crossfade_final", 0.0) + (plano.get("duracao_encerramento", 0.0) if plano.get("encerramento") else 0.0)
    print("\nCONFERÊNCIA")
    print(informacoes)
    print("  ".join(linhas_loudness))
    print(f"duração esperada: {duracao_esperada:.2f} s ({duracao_esperada / 60:.1f} min)")


def principal():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    pasta_edicao = Path(sys.argv[1]).expanduser().resolve()
    refazer_todas = "--refazer-partes" in sys.argv
    configuracao = json.load(open(pasta_edicao / "config_editor.json", encoding="utf-8"))
    caminho_plano = pasta_edicao / "_edicao" / "plano.json"
    plano = json.load(open(caminho_plano, encoding="utf-8"))
    pasta_resultado = Path(plano.get("pasta_resultado", pasta_edicao / "Resultado Final"))
    pasta_resultado.mkdir(parents=True, exist_ok=True)
    nome_saida = plano.get("nome_saida", "Video_editado")
    total_partes = len(plano["partes"])

    if "--previas" in sys.argv:
        segundos_inicio = configuracao.get("previa_inicio_s", 60)
        segundos_fim = configuracao.get("previa_fim_s", 30)
        indices_inicio = [indice for indice, (inicio, _) in enumerate(plano["partes"]) if inicio < segundos_inicio]
        inicio_do_fim = plano["fim_video"] - segundos_fim
        indices_fim = [indice for indice, (_, fim) in enumerate(plano["partes"]) if fim > inicio_do_fim]
        montar_audio(caminho_plano)
        renderizar_partes(caminho_plano, plano, sorted(set(indices_inicio + indices_fim)), refazer_todas)
        pasta_previas = pasta_resultado / "Previas"
        pasta_previas.mkdir(exist_ok=True)
        rodar_script("juntar_final.py", caminho_plano, pasta_previas / f"previa_inicio_{segundos_inicio}s.mp4", f"--ate={segundos_inicio}")
        rodar_script("juntar_final.py", caminho_plano, pasta_previas / f"previa_fim_{segundos_fim}s.mp4", f"--ultimos={segundos_fim}")
        print(f"\nPrévias prontas em: {pasta_previas}")
        return

    if "--final" in sys.argv:
        montar_audio(caminho_plano)
        renderizar_partes(caminho_plano, plano, range(total_partes), refazer_todas)
        caminho_video = pasta_resultado / f"{nome_saida}.mp4"
        rodar_script("juntar_final.py", caminho_plano, caminho_video)
        pasta_trabalho = Path(plano["pasta_trabalho"])
        for nome_arquivo in ("capitulos.txt", "cortes.csv"):
            if (pasta_trabalho / nome_arquivo).exists():
                shutil.copy(pasta_trabalho / nome_arquivo, pasta_resultado / nome_arquivo)
        conferir_video(caminho_video, plano)
        print(f"\nVídeo final: {caminho_video}")
        return

    print(__doc__)
    sys.exit(1)


if __name__ == "__main__":
    principal()
