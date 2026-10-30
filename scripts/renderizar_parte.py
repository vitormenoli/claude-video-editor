"""Renderiza UMA parte do vídeo editado (só imagem), para caber no limite de tempo de cada comando.

Lê o plano.json (trechos mantidos do bruto + motions + transições, tudo em tempo de saída) e gera
partes/parte_NNN.mp4 com H.264 1920x1080 30 fps CRF 18 preset veryfast. As partes são juntadas depois
sem recompressão (concat demuxer).

Uso: python3 renderizar_parte.py <plano.json> <indice_da_parte> [--mostrar-comando]
"""
import json
import os
import subprocess
import sys

QUADROS_POR_SEGUNDO = 30
DISTANCIA_MAXIMA_NO_MESMO_GRUPO = 8.0
TELA_DIVIDIDA_X, TELA_DIVIDIDA_Y, TELA_DIVIDIDA_LARGURA, TELA_DIVIDIDA_ALTURA = 592, 180, 1280, 720


def trechos_de_saida(plano):
    """Converte os trechos do bruto em blocos com tempo de saída."""
    blocos = []
    tempo_saida = 0.0
    for inicio_fonte, fim_fonte in plano["trechos"]:
        blocos.append({"inicio_fonte": inicio_fonte, "fim_fonte": fim_fonte, "inicio_saida": tempo_saida, "fim_saida": tempo_saida + (fim_fonte - inicio_fonte)})
        tempo_saida += fim_fonte - inicio_fonte
    return blocos


def pedacos_da_parte(blocos, inicio_parte, fim_parte):
    """Pedaços do bruto que caem dentro do intervalo de saída desta parte."""
    pedacos = []
    for bloco in blocos:
        inicio_saida = max(bloco["inicio_saida"], inicio_parte)
        fim_saida = min(bloco["fim_saida"], fim_parte)
        if fim_saida - inicio_saida < 0.5 / QUADROS_POR_SEGUNDO:
            continue
        deslocamento = inicio_saida - bloco["inicio_saida"]
        pedacos.append({"inicio_fonte": bloco["inicio_fonte"] + deslocamento, "fim_fonte": bloco["inicio_fonte"] + deslocamento + (fim_saida - inicio_saida)})
    return pedacos


def agrupar_pedacos(pedacos):
    """Pedaços próximos no bruto dividem a mesma entrada (evita abrir o arquivo dezenas de vezes)."""
    grupos = []
    for pedaco in pedacos:
        if grupos and pedaco["inicio_fonte"] - grupos[-1]["fim_fonte"] < DISTANCIA_MAXIMA_NO_MESMO_GRUPO and pedaco["inicio_fonte"] >= grupos[-1]["fim_fonte"] - 0.001:
            grupos[-1]["pedacos"].append(pedaco)
            grupos[-1]["fim_fonte"] = pedaco["fim_fonte"]
        else:
            grupos.append({"inicio_fonte": pedaco["inicio_fonte"], "fim_fonte": pedaco["fim_fonte"], "pedacos": [pedaco]})
    return grupos


def montar_comando(plano, indice_parte):
    pasta_trabalho = plano["pasta_trabalho"]
    inicio_parte, fim_parte = plano["partes"][indice_parte]
    duracao_parte = fim_parte - inicio_parte
    blocos = trechos_de_saida(plano)
    grupos = agrupar_pedacos(pedacos_da_parte(blocos, inicio_parte, fim_parte))

    argumentos_entrada = []
    filtros = []
    rotulos_pedacos = []
    for indice_grupo, grupo in enumerate(grupos):
        inicio_leitura = max(0.0, grupo["inicio_fonte"] - 1.0)
        duracao_leitura = grupo["fim_fonte"] - inicio_leitura + 0.5
        argumentos_entrada += ["-ss", f"{inicio_leitura:.4f}", "-t", f"{duracao_leitura:.4f}", "-i", plano["video_bruto"]]
        quantidade = len(grupo["pedacos"])
        rotulos_divisao = [f"g{indice_grupo}d{indice}" for indice in range(quantidade)]
        if quantidade > 1:
            filtros.append(f"[{indice_grupo}:v]split={quantidade}" + "".join(f"[{rotulo}]" for rotulo in rotulos_divisao))
        else:
            rotulos_divisao = [f"{indice_grupo}:v"]
        for indice_pedaco, pedaco in enumerate(grupo["pedacos"]):
            rotulo_saida = f"p{indice_grupo}_{indice_pedaco}"
            inicio_relativo = pedaco["inicio_fonte"] - inicio_leitura
            fim_relativo = pedaco["fim_fonte"] - inicio_leitura
            quadros_do_pedaco = round((pedaco["fim_fonte"] - pedaco["inicio_fonte"]) * QUADROS_POR_SEGUNDO)
            filtros.append(f"[{rotulos_divisao[indice_pedaco]}]trim=start={inicio_relativo:.4f}:end={fim_relativo + 0.1:.4f},setpts=PTS-STARTPTS,fps={QUADROS_POR_SEGUNDO},"
                           f"tpad=stop_mode=clone:stop_duration=0.2,trim=end_frame={quadros_do_pedaco},setpts=PTS-STARTPTS[{rotulo_saida}]")
            rotulos_pedacos.append(rotulo_saida)
    filtros.append("".join(f"[{rotulo}]" for rotulo in rotulos_pedacos) + f"concat=n={len(rotulos_pedacos)}:v=1:a=0,setpts=N/({QUADROS_POR_SEGUNDO}*TB),scale=1920:1080,setsar=1,format=yuv420p,"
                   f"tpad=stop_mode=clone:stop_duration=0.5,trim=end_frame={round(duracao_parte * QUADROS_POR_SEGUNDO)},setpts=PTS-STARTPTS[base]")

    # Desfoque de regiões da tela gravada (ex.: texto que não pode aparecer), aplicado antes de tudo
    # para valer também na tela reduzida do layout dividido. O desfoque é feito em 1/4 da resolução
    # (mesmo visual e bem mais rápido, para a parte caber no limite de 45 s do comando).
    rotulo_base = "base"
    desfoques_da_parte = [desfoque for desfoque in plano.get("desfoques", []) if desfoque["inicio"] < fim_parte and desfoque["fim"] > inicio_parte]
    for indice_desfoque, desfoque in enumerate(desfoques_da_parte):
        inicio_local = max(0.0, desfoque["inicio"] - inicio_parte)
        fim_local = min(duracao_parte, desfoque["fim"] - inicio_parte)
        rotulo_limpo, rotulo_recorte, rotulo_desfocado, rotulo_resultado = (f"semdesfoque{indice_desfoque}", f"recorte{indice_desfoque}",
                                                                            f"desfocado{indice_desfoque}", f"comdesfoque{indice_desfoque}")
        filtros.append(f"[{rotulo_base}]split=2[{rotulo_limpo}][{rotulo_recorte}]")
        filtros.append(f"[{rotulo_recorte}]crop={desfoque['largura']}:{desfoque['altura']}:{desfoque['x']}:{desfoque['y']},scale=iw/4:ih/4,boxblur=luma_radius=7:luma_power=3:chroma_radius=4:chroma_power=2,scale={desfoque['largura']}:{desfoque['altura']}[{rotulo_desfocado}]")
        filtros.append(f"[{rotulo_limpo}][{rotulo_desfocado}]overlay={desfoque['x']}:{desfoque['y']}:enable='between(t,{inicio_local:.3f},{fim_local:.3f})'[{rotulo_resultado}]")
        rotulo_base = rotulo_resultado

    motions_da_parte = [motion for motion in plano["motions"] if motion["inicio"] < fim_parte and motion["inicio"] + motion["duracao"] > inicio_parte]
    motions_divididos = [motion for motion in motions_da_parte if motion["modo"] == "dividido"]
    rotulo_atual = rotulo_base
    rotulos_tela_reduzida = []
    if motions_divididos:
        rotulos_copias = [f"copia{indice}" for indice in range(len(motions_divididos))]
        filtros.append(f"[{rotulo_base}]split={len(motions_divididos) + 1}[principal]" + "".join(f"[{rotulo}]" for rotulo in rotulos_copias))
        rotulo_atual = "principal"
        for indice, (motion, rotulo_copia) in enumerate(zip(motions_divididos, rotulos_copias)):
            inicio_local = motion["inicio"] - inicio_parte
            entrada_tela = inicio_local + 0.3
            saida_tela = inicio_local + motion["duracao"] - 0.35
            rotulo_reduzida = f"reduzida{indice}"
            filtros.append(f"[{rotulo_copia}]scale={TELA_DIVIDIDA_LARGURA}:{TELA_DIVIDIDA_ALTURA},format=yuva420p,"
                           f"fade=t=in:st={max(0.0, entrada_tela):.3f}:d=0.25:alpha=1,fade=t=out:st={max(0.0, saida_tela - 0.25):.3f}:d=0.25:alpha=1[{rotulo_reduzida}]")
            rotulos_tela_reduzida.append((motion, rotulo_reduzida, entrada_tela, saida_tela))

    proximo_indice_entrada = len(grupos)
    for indice_motion, motion in enumerate(motions_da_parte):
        deslocamento_no_motion = max(0.0, inicio_parte - motion["inicio"])
        argumentos_entrada += ["-c:v", "libvpx-vp9"]
        if deslocamento_no_motion > 0:
            argumentos_entrada += ["-ss", f"{deslocamento_no_motion:.4f}"]
        argumentos_entrada += ["-i", os.path.join(pasta_trabalho, "motions", motion["arquivo"])]
        atraso = max(0.0, motion["inicio"] - inicio_parte)
        rotulo_motion = f"m{indice_motion}"
        filtros.append(f"[{proximo_indice_entrada}:v]format=yuva420p,setpts=PTS-STARTPTS+{atraso:.4f}/TB[{rotulo_motion}]")
        rotulo_novo = f"comp{indice_motion}"
        filtros.append(f"[{rotulo_atual}][{rotulo_motion}]overlay=0:0:eof_action=pass:repeatlast=0:format=auto[{rotulo_novo}]")
        rotulo_atual = rotulo_novo
        for motion_dividido, rotulo_reduzida, entrada_tela, saida_tela in rotulos_tela_reduzida:
            if motion_dividido is motion:
                rotulo_com_tela = f"tela{indice_motion}"
                filtros.append(f"[{rotulo_atual}][{rotulo_reduzida}]overlay={TELA_DIVIDIDA_X}:{TELA_DIVIDIDA_Y}:enable='between(t,{max(0.0, entrada_tela):.3f},{saida_tela:.3f})'[{rotulo_com_tela}]")
                rotulo_atual = rotulo_com_tela
        proximo_indice_entrada += 1

    if plano.get("fade_final") and indice_parte == len(plano["partes"]) - 1:
        filtros.append(f"[{rotulo_atual}]fade=t=out:st={duracao_parte - plano['fade_final']:.3f}:d={plano['fade_final']:.3f}[comfade]")
        rotulo_atual = "comfade"
    filtros.append(f"[{rotulo_atual}]format=yuv420p[saida]")

    caminho_filtro = os.path.join(pasta_trabalho, "partes", f"filtro_{indice_parte:03d}.txt")
    os.makedirs(os.path.dirname(caminho_filtro), exist_ok=True)
    with open(caminho_filtro, "w") as arquivo_filtro:
        arquivo_filtro.write(";\n".join(filtros))
    caminho_saida = os.path.join(pasta_trabalho, "partes", f"parte_{indice_parte:03d}.mp4")
    comando = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + argumentos_entrada + [
        "-filter_complex_script", caminho_filtro, "-map", "[saida]", "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-r", str(QUADROS_POR_SEGUNDO), "-g", "60", "-x264-params", "keyint=60:min-keyint=30",
        "-frames:v", str(round(duracao_parte * QUADROS_POR_SEGUNDO)), "-video_track_timescale", "15360", caminho_saida]
    return comando, caminho_saida


if __name__ == "__main__":
    plano = json.load(open(sys.argv[1], encoding="utf-8"))
    indice = int(sys.argv[2])
    comando, caminho_saida = montar_comando(plano, indice)
    if "--mostrar-comando" in sys.argv:
        print(" ".join(comando))
    resultado = subprocess.run(comando)
    if resultado.returncode != 0:
        sys.exit(resultado.returncode)
    print("ok", caminho_saida)
