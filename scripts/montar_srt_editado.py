"""Gera a legenda .srt a partir da transcrição do ÁUDIO JÁ EDITADO (mesma linha do tempo do vídeo final).

Assim a legenda não herda nenhum erro de encaixe dos cortes. Aplica as correções de texto do decisoes.json
(nomes próprios que o Whisper erra) e quebra em blocos de até 42 caracteres e 4 s.

Uso: python3 montar_srt_editado.py <transcricao_editado_palavras.jsonl> <decisoes.json> <saida.srt> [duracao_video]
"""
import json
import re
import sys

MAXIMO_CARACTERES = 42
MAXIMO_SEGUNDOS = 4.0
PAUSA_QUE_QUEBRA = 0.6


def formatar_tempo(segundos):
    milissegundos = int(round(segundos * 1000))
    horas, resto = divmod(milissegundos, 3600000)
    minutos, resto = divmod(resto, 60000)
    segundos_inteiros, milissegundos = divmod(resto, 1000)
    return f"{horas:02d}:{minutos:02d}:{segundos_inteiros:02d},{milissegundos:03d}"


def normalizar(texto):
    return re.sub(r"[^\wÀ-ú-]", "", texto.lower())


def aplicar_correcoes_nas_palavras(palavras, correcoes):
    """Correções por sequência de palavras (vale mesmo quando o trecho errado cai entre dois blocos da legenda).
    A pontuação colada na última palavra errada é mantida."""
    for errado, certo in sorted(correcoes, key=lambda par: -len(par[0].split())):
        alvo = [normalizar(pedaco) for pedaco in errado.split()]
        indice = 0
        resultado = []
        while indice < len(palavras):
            trecho = palavras[indice:indice + len(alvo)]
            if len(trecho) == len(alvo) and [normalizar(item["palavra"]) for item in trecho] == alvo:
                pontuacao_final = re.sub(r"^.*?([.,?!]*)$", r"\1", trecho[-1]["palavra"].strip())
                resultado.append({"inicio": trecho[0]["inicio"], "fim": trecho[-1]["fim"], "palavra": " " + certo + pontuacao_final})
                indice += len(alvo)
            else:
                resultado.append(palavras[indice])
                indice += 1
        palavras = resultado
    return palavras


def principal():
    caminho_transcricao, caminho_decisoes, caminho_saida = sys.argv[1:4]
    duracao_video = float(sys.argv[4]) if len(sys.argv) > 4 else None
    correcoes = [tuple(par) for par in json.load(open(caminho_decisoes, encoding="utf-8")).get("correcoes_texto", [])]
    palavras = []
    for linha in open(caminho_transcricao, encoding="utf-8"):
        palavras.extend(json.loads(linha)["palavras"])
    palavras = aplicar_correcoes_nas_palavras([palavra for palavra in palavras if palavra["palavra"].strip()], correcoes)
    blocos = []
    atual = []
    for palavra in palavras:
        texto_palavra = palavra["palavra"].strip()
        if not texto_palavra:
            continue
        if atual:
            texto_atual = " ".join(item["palavra"].strip() for item in atual)
            estoura = len(texto_atual) + 1 + len(texto_palavra) > MAXIMO_CARACTERES
            longo_demais = palavra["fim"] - atual[0]["inicio"] > MAXIMO_SEGUNDOS
            pausa = palavra["inicio"] - atual[-1]["fim"] > PAUSA_QUE_QUEBRA
            fim_de_frase = atual[-1]["palavra"].strip()[-1:] in ".?!" and len(texto_atual) > 12
            if estoura or longo_demais or pausa or fim_de_frase:
                blocos.append(atual)
                atual = []
        atual.append(palavra)
    if atual:
        blocos.append(atual)
    with open(caminho_saida, "w", encoding="utf-8") as arquivo:
        for indice, bloco in enumerate(blocos):
            inicio = bloco[0]["inicio"]
            fim = bloco[-1]["fim"] + 0.15
            if indice + 1 < len(blocos):
                fim = min(fim, blocos[indice + 1][0]["inicio"] - 0.02)
            if duracao_video is not None:
                fim = min(fim, duracao_video)
            texto = " ".join(item["palavra"].strip() for item in bloco)
            arquivo.write(f"{indice + 1}\n{formatar_tempo(inicio)} --> {formatar_tempo(max(fim, inicio + 0.3))}\n{texto}\n\n")
    print(f"{len(blocos)} blocos")


if __name__ == "__main__":
    principal()
