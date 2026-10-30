"""Converte o roteiro de motions (ancorado em frases/tempos do BRUTO) em:
  - especificacoes_motions.json  para o renderizador de motions (motor.html + renderizar.js)
  - plano.json                   para o render no computador (trechos, motions em tempo de saída, efeitos, partes)
  - capitulos.txt                no formato "0:00 Título" para a descrição do YouTube

Uso: python3 planejar.py <transcricao.jsonl> <mapa_tempo.json> <roteiro_motions.json> <pasta_saida> [--ate=SEGUNDOS_DE_SAIDA]
"""
import json
import re
import sys
import unicodedata

QUADROS_POR_SEGUNDO = 30
DURACAO_PARTE_ALVO = 40.0

SONS_POR_TIPO = {
    "abertura": [("sfx_sopro.wav", 0.0), ("sfx_pop.wav", 1.1)],
    "capitulo": [("sfx_sopro.wav", 0.0)],
    "pilula": [("sfx_pop.wav", 0.02)],
    "comando": [("sfx_digitacao.wav", 0.3)],
    "comparacao": [("sfx_sopro.wav", 0.0), ("sfx_contador.wav", 0.9), ("sfx_contador.wav", 1.8), ("sfx_impacto.wav", 3.2)],
    "painel": [("sfx_sopro.wav", 0.0)],
    "grafo": [("sfx_sopro.wav", 0.0)],
    "leitura": [("sfx_sopro.wav", 0.0), ("sfx_contador.wav", 1.0)],
    "numero": [("sfx_sopro.wav", 0.0), ("sfx_pop.wav", 0.3)],
    "transicao": [("sfx_sopro.wav", 0.0)],
    "imagem": [("sfx_sopro.wav", 0.0), ("sfx_pop.wav", 0.9)],
    "ilustracao": [("sfx_sopro.wav", 0.0), ("sfx_pop.wav", 0.45)],
}
MODO_POR_TIPO = {"abertura": "sobreposto", "capitulo": "sobreposto", "pilula": "sobreposto", "comando": "sobreposto", "transicao": "sobreposto",
                 "comparacao": "tela_cheia", "grafo": "tela_cheia", "leitura": "tela_cheia", "numero": "tela_cheia", "painel": "tela_cheia", "imagem": "sobreposto",
                 "ilustracao": "sobreposto"}


def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(caractere for caractere in texto if unicodedata.category(caractere) != "Mn")
    return re.sub(r"[^a-z0-9%]", "", texto)


def carregar_palavras(caminho):
    palavras = []
    for linha in open(caminho, encoding="utf-8"):
        palavras.extend(json.loads(linha)["palavras"])
    palavras.sort(key=lambda palavra: palavra["inicio"])
    for palavra in palavras:
        palavra["normalizada"] = normalizar(palavra["palavra"])
    return [palavra for palavra in palavras if palavra["normalizada"]]


def achar_frase(palavras, frase, depois_de):
    """Primeira ocorrência da frase depois do tempo informado (tempo do bruto). Devolve (inicio, fim)."""
    alvo = [normalizar(pedaco) for pedaco in frase.split() if normalizar(pedaco)]
    for indice in range(len(palavras) - len(alvo) + 1):
        if palavras[indice]["inicio"] < depois_de:
            continue
        if all(palavras[indice + deslocamento]["normalizada"] == alvo[deslocamento] for deslocamento in range(len(alvo))):
            return palavras[indice]["inicio"], palavras[indice + len(alvo) - 1]["fim"]
    raise ValueError(f"frase não encontrada depois de {depois_de}: {frase}")


def fonte_para_saida(tempo_fonte, mapa):
    """Tempo do bruto -> tempo do vídeo editado. Se o instante foi cortado, usa o início do próximo trecho mantido."""
    for trecho in mapa:
        if tempo_fonte < trecho["inicio_fonte"]:
            return trecho["inicio_saida"]
        if tempo_fonte <= trecho["fim_fonte"]:
            return trecho["inicio_saida"] + (tempo_fonte - trecho["inicio_fonte"])
    ultimo = mapa[-1]
    return ultimo["inicio_saida"] + (ultimo["fim_fonte"] - ultimo["inicio_fonte"])


def formatar_capitulo(segundos):
    segundos = int(segundos)
    if segundos >= 3600:
        return f"{segundos // 3600}:{(segundos % 3600) // 60:02d}:{segundos % 60:02d}"
    return f"{segundos // 60}:{segundos % 60:02d}"


def principal():
    caminho_transcricao, caminho_mapa, caminho_roteiro, pasta_saida = sys.argv[1:5]
    limite_saida = None
    for argumento in sys.argv[5:]:
        if argumento.startswith("--ate="):
            limite_saida = float(argumento[6:])
    palavras = carregar_palavras(caminho_transcricao)
    mapa = json.load(open(caminho_mapa))
    roteiro = json.load(open(caminho_roteiro, encoding="utf-8"))
    duracao_saida = mapa[-1]["inicio_saida"] + (mapa[-1]["fim_fonte"] - mapa[-1]["inicio_fonte"])

    especificacoes = []
    motions_plano = []
    efeitos = []
    capitulos = []
    for indice, item in enumerate(roteiro["motions"]):
        if "frase" in item:
            try:
                inicio_frase, fim_frase = achar_frase(palavras, item["frase"], item.get("depois_de", 0.0))
            except ValueError as erro:
                print("ERRO:", erro)
                continue
            ancora_fonte = inicio_frase if item.get("ancora", "inicio") == "inicio" else fim_frase
        else:
            ancora_fonte = item["tempo_fonte"]
        inicio_saida = round((fonte_para_saida(ancora_fonte, mapa) + item.get("ajuste", 0.0)) * QUADROS_POR_SEGUNDO) / QUADROS_POR_SEGUNDO
        inicio_saida = max(0.0, inicio_saida)
        if limite_saida is not None and inicio_saida > limite_saida:
            continue
        especificacao = dict(item["motion"])
        nome = item.get("nome", f"m{indice:03d}_{especificacao['tipo']}")
        especificacao["nome"] = nome
        especificacoes.append(especificacao)
        modo = item.get("modo", MODO_POR_TIPO[especificacao["tipo"]])
        if especificacao.get("layout") == "dividido":
            modo = "dividido"
        if especificacao.get("fundoCheio"):
            modo = "tela_cheia"
        motions_plano.append({"arquivo": nome + ".webm", "inicio": inicio_saida, "duracao": especificacao["duracao"], "modo": modo, "tipo": especificacao["tipo"]})
        for arquivo_som, deslocamento in item.get("sons", SONS_POR_TIPO[especificacao["tipo"]]):
            efeitos.append({"arquivo": arquivo_som, "tempo": round(inicio_saida + deslocamento, 3)})
        if especificacao["tipo"] == "capitulo" or item.get("capitulo"):
            capitulos.append((inicio_saida if especificacao["tipo"] == "capitulo" else inicio_saida, item.get("capitulo", especificacao.get("titulo"))))

    # Sobreposição: nunca mais de um elemento ao mesmo tempo (aviso para revisão manual).
    ordenados = sorted(motions_plano, key=lambda motion: motion["inicio"])
    for anterior, seguinte in zip(ordenados, ordenados[1:]):
        if seguinte["inicio"] < anterior["inicio"] + anterior["duracao"] - 0.05 and "transicao" not in (anterior["tipo"], seguinte["tipo"]):
            print(f"AVISO: {anterior['arquivo']} ({anterior['inicio']:.1f}s) sobrepõe {seguinte['arquivo']} ({seguinte['inicio']:.1f}s)")

    fim_render = duracao_saida if limite_saida is None else min(duracao_saida, limite_saida)
    partes = []
    inicio_parte = 0.0
    while inicio_parte < fim_render - 0.01:
        fim_parte = min(fim_render, inicio_parte + DURACAO_PARTE_ALVO)
        if fim_render - fim_parte < 8.0:
            fim_parte = fim_render
        fim_parte = round(fim_parte * QUADROS_POR_SEGUNDO) / QUADROS_POR_SEGUNDO
        partes.append([round(inicio_parte, 4), round(fim_parte, 4)])
        inicio_parte = fim_parte

    plano = dict(roteiro["configuracao"])
    plano["trechos"] = [[trecho["inicio_fonte"], trecho["fim_fonte"]] for trecho in mapa]
    plano["motions"] = ordenados
    plano["efeitos_sonoros"] = sorted(efeitos, key=lambda efeito: efeito["tempo"])
    plano["partes"] = partes
    plano["fim_video"] = round(duracao_saida, 4)
    # Desfoques definidos em tempo do BRUTO viram intervalos no tempo de saída (um por trecho mantido que eles cruzam).
    desfoques_saida = []
    for desfoque in roteiro.get("desfoques_fonte", []):
        for trecho in mapa:
            inicio_sobreposto = max(desfoque["inicio"], trecho["inicio_fonte"])
            fim_sobreposto = min(desfoque["fim"], trecho["fim_fonte"])
            if fim_sobreposto > inicio_sobreposto:
                desfoques_saida.append({"inicio": round(trecho["inicio_saida"] + (inicio_sobreposto - trecho["inicio_fonte"]), 4),
                                        "fim": round(trecho["inicio_saida"] + (fim_sobreposto - trecho["inicio_fonte"]), 4),
                                        "x": desfoque["x"], "y": desfoque["y"], "largura": desfoque["largura"], "altura": desfoque["altura"]})
    # Intervalos colados (trechos vizinhos do mesmo desfoque) viram um só, para o filtro do render ficar leve.
    desfoques_unidos = []
    for desfoque in sorted(desfoques_saida, key=lambda item: (item["x"], item["y"], item["largura"], item["altura"], item["inicio"])):
        anterior = desfoques_unidos[-1] if desfoques_unidos else None
        mesma_regiao = anterior is not None and all(anterior[chave] == desfoque[chave] for chave in ("x", "y", "largura", "altura"))
        if mesma_regiao and desfoque["inicio"] - anterior["fim"] < 0.05:
            anterior["fim"] = max(anterior["fim"], desfoque["fim"])
        else:
            desfoques_unidos.append(dict(desfoque))
    plano["desfoques"] = sorted(desfoques_unidos, key=lambda item: item["inicio"])
    json.dump(especificacoes, open(f"{pasta_saida}/especificacoes_motions.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(plano, open(f"{pasta_saida}/plano.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(f"{pasta_saida}/capitulos.txt", "w", encoding="utf-8") as arquivo_capitulos:
        capitulos_ordenados = sorted(capitulos)
        if capitulos_ordenados and capitulos_ordenados[0][0] > 0:
            capitulos_ordenados[0] = (0.0, capitulos_ordenados[0][1])
        for tempo, titulo in capitulos_ordenados:
            arquivo_capitulos.write(f"{formatar_capitulo(tempo)} {titulo}\n")
    print(f"{len(especificacoes)} motions, {len(efeitos)} efeitos, {len(partes)} partes, saída {duracao_saida / 60:.2f} min")


if __name__ == "__main__":
    principal()
