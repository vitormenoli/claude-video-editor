"""Junta as partes renderizadas + o encerramento fixo e coloca o áudio final, sem recomprimir as partes.

O encerramento (Intro Logo animada.mp4) é só recodificado com os mesmos parâmetros das partes para o concat
funcionar; a duração, a velocidade e a imagem dele não mudam. Nada é sobreposto nele.

Uso: python3 juntar_final.py <plano.json> <caminho_saida.mp4> [--ate=SEGUNDOS]  (o --ate gera prévias)
     python3 juntar_final.py <plano.json> <caminho_saida.mp4> --ultimos=30      (prévia do fim, com o encerramento)
"""
import json
import os
import subprocess
import sys


def recodificar_encerramento(plano):
    caminho_saida = os.path.join(plano["pasta_trabalho"], "partes", "encerramento_30fps.mp4")
    if not os.path.exists(caminho_saida):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", plano["encerramento"], "-an", "-vf", "fps=30,scale=1920:1080,setsar=1,format=yuv420p",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", "30",
                        "-g", "60", "-x264-params", "keyint=60:min-keyint=30", "-video_track_timescale", "15360", caminho_saida], check=True)
    return caminho_saida


def montar_final_com_crossfade(plano, caminho_ultima_parte, duracao_crossfade):
    """Última parte + encerramento mesclados (crossfade), recodificados com os mesmos parâmetros das partes.
    O encerramento entra inteiro: o crossfade só sobrepõe o começo dele ao fim do vídeo."""
    caminho_encerramento = recodificar_encerramento(plano)
    caminho_saida = os.path.join(plano["pasta_trabalho"], "partes", "final_com_encerramento.mp4")
    inicio_parte, fim_parte = plano["partes"][-1]
    deslocamento = (fim_parte - inicio_parte) - duracao_crossfade
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", caminho_ultima_parte, "-i", caminho_encerramento,
                    "-filter_complex", f"[0:v][1:v]xfade=transition=fade:duration={duracao_crossfade}:offset={deslocamento:.4f},format=yuv420p[saida]",
                    "-map", "[saida]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", "30",
                    "-g", "60", "-x264-params", "keyint=60:min-keyint=30", "-video_track_timescale", "15360", caminho_saida], check=True)
    return caminho_saida


def principal():
    plano = json.load(open(sys.argv[1], encoding="utf-8"))
    caminho_saida = sys.argv[2]
    limite = None
    ultimos = None
    for argumento in sys.argv[3:]:
        if argumento.startswith("--ate="):
            limite = float(argumento[6:])
        if argumento.startswith("--ultimos="):
            ultimos = float(argumento[10:])
    pasta_partes = os.path.join(plano["pasta_trabalho"], "partes")
    caminho_lista = os.path.join(pasta_partes, "lista_concat.txt")
    arquivos_partes = [os.path.join(pasta_partes, f"parte_{indice:03d}.mp4") for indice in range(len(plano["partes"]))]
    incluir_encerramento = limite is None
    duracao_crossfade = plano.get("crossfade_final", 0.0)
    with open(caminho_lista, "w") as arquivo_lista:
        partes_normais = arquivos_partes[:-1] if incluir_encerramento and duracao_crossfade > 0 else arquivos_partes
        for caminho_parte in partes_normais:
            if os.path.exists(caminho_parte):
                arquivo_lista.write(f"file '{caminho_parte}'\n")
        if incluir_encerramento and duracao_crossfade > 0:
            arquivo_lista.write(f"file '{montar_final_com_crossfade(plano, arquivos_partes[-1], duracao_crossfade)}'\n")
        elif incluir_encerramento:
            arquivo_lista.write(f"file '{recodificar_encerramento(plano)}'\n")
    caminho_audio = os.path.join(plano["pasta_trabalho"], "audio", "audio_final.m4a")
    comando = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", caminho_lista, "-i", caminho_audio,
               "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart"]
    if limite is not None:
        comando += ["-t", str(limite)]
    if ultimos is not None:
        # Prévia do fim: só as partes que cobrem os últimos segundos (as do meio podem ainda não ter sido renderizadas).
        duracao_total = plano["fim_video"] - duracao_crossfade + plano["duracao_encerramento"]
        inicio_previa = max(0.0, duracao_total - ultimos)
        indice_primeira_parte = max(indice for indice, (inicio_parte, _) in enumerate(plano["partes"]) if inicio_parte <= inicio_previa)
        inicio_primeira_parte = plano["partes"][indice_primeira_parte][0]
        caminho_lista_fim = os.path.join(pasta_partes, "lista_concat_fim.txt")
        with open(caminho_lista_fim, "w") as arquivo_lista_fim:
            for caminho_parte in arquivos_partes[indice_primeira_parte:-1]:
                arquivo_lista_fim.write(f"file '{caminho_parte}'\n")
            arquivo_lista_fim.write(f"file '{montar_final_com_crossfade(plano, arquivos_partes[-1], duracao_crossfade)}'\n")
        comando = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", caminho_lista_fim,
                   "-ss", f"{inicio_primeira_parte:.4f}", "-i", caminho_audio,
                   "-map", "0:v", "-map", "1:a", "-ss", f"{inicio_previa - inicio_primeira_parte:.4f}",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    comando.append(caminho_saida)
    subprocess.run(comando, check=True)
    print("ok", caminho_saida)


if __name__ == "__main__":
    principal()
