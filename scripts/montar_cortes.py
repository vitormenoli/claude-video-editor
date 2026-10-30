"""Monta a lista de cortes do bruto a partir da transcrição (palavras com tempo), dos silêncios do FFmpeg
e das decisões manuais (retomadas, trecho do teste refeito etc.).

Saídas na pasta indicada:
  cortes.csv            início, fim, motivo, trecho da transcrição (tempos do BRUTO)
  trechos_mantidos.json lista de [inicio, fim] do bruto que ficam, na ordem, alinhados à grade de 30 fps
  mapa_tempo.json       os mesmos trechos com o tempo de saída correspondente
  legenda.srt           transcrição já no tempo do vídeo editado (para subir no YouTube)
  transcricao_editada.txt texto corrido do que ficou, com o tempo de saída

Uso: python3 montar_cortes.py <transcricao.jsonl> <silencios_ffmpeg.txt> <decisoes.json> <pasta_saida> [transcricao_disfluencias.jsonl]
"""
import csv
import json
import re
import sys
import unicodedata

QUADROS_POR_SEGUNDO = 30
LIMIAR_SILENCIO = 0.45
RESPIRO = 0.08
JANELA_GAGUEIRA = 1.2
LACUNA_SEM_FALA = 1.5
PAUSA_REAL_LACUNA = 0.3
FRACAO_MAXIMA_VOZ_NA_LACUNA = 0.3
PALAVRAS_DE_ENFASE = {"muito", "menos"}


def normalizar_palavra(texto):
    sem_acento = unicodedata.normalize("NFD", texto.lower())
    sem_acento = "".join(caractere for caractere in sem_acento if unicodedata.category(caractere) != "Mn")
    return re.sub(r"[^a-z0-9]", "", sem_acento)


def carregar_palavras(caminho_transcricao):
    palavras = []
    for linha in open(caminho_transcricao, encoding="utf-8"):
        segmento = json.loads(linha)
        for palavra in segmento["palavras"]:
            if palavra["fim"] > palavra["inicio"]:
                palavras.append(palavra)
    palavras.sort(key=lambda palavra: palavra["inicio"])
    return palavras


def carregar_silencios(caminho_silencios):
    silencios = []
    for linha in open(caminho_silencios):
        correspondencia = re.search(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", linha)
        if correspondencia:
            fim = float(correspondencia.group(1))
            silencios.append((fim - float(correspondencia.group(2)), fim))
    return silencios


def trecho_da_transcricao(palavras, inicio, fim):
    textos = [palavra["palavra"].strip() for palavra in palavras if palavra["inicio"] < fim and palavra["fim"] > inicio]
    texto = " ".join(textos)
    return texto if len(texto) < 160 else texto[:157] + "..."


def detectar_gagueiras(palavras, intervalos_ja_removidos):
    """Gagueira, repetição e falso começo, sempre saindo a PRIMEIRA ocorrência (fica a última versão):
    1) o mesmo grupo de 1 a 6 palavras repetido logo em seguida ("pra descobrir, pra descobrir");
    2) começo de frase abandonado: um grupo de 2+ palavras, de 1 a 3 palavras soltas terminando em "..." ou "-",
       e o mesmo grupo de novo ("Lembrando que eu... Lembrando que você")."""
    cortes_gagueira = []
    normalizadas = [normalizar_palavra(palavra["palavra"]) for palavra in palavras]

    def ja_removido(tempo):
        return any(inicio <= tempo < fim for inicio, fim, _ in intervalos_ja_removidos + cortes_gagueira)

    def termina_frase(indice_palavra):
        return palavras[indice_palavra]["palavra"].strip().endswith((".", "?", "!"))

    indice = 0
    while indice < len(palavras) - 1:
        encontrou = False
        for tamanho_grupo in (6, 5, 4, 3, 2, 1):
            if indice + 2 * tamanho_grupo > len(palavras):
                continue
            primeiro_grupo = normalizadas[indice:indice + tamanho_grupo]
            segundo_grupo = normalizadas[indice + tamanho_grupo:indice + 2 * tamanho_grupo]
            if not all(primeiro_grupo) or primeiro_grupo != segundo_grupo:
                continue
            if tamanho_grupo == 1 and primeiro_grupo[0] in PALAVRAS_DE_ENFASE:
                continue
            if termina_frase(indice + tamanho_grupo - 1):
                continue
            inicio_primeiro = palavras[indice]["inicio"]
            inicio_segundo = palavras[indice + tamanho_grupo]["inicio"]
            if inicio_segundo - inicio_primeiro >= JANELA_GAGUEIRA * tamanho_grupo + 0.6 or ja_removido(inicio_primeiro):
                continue
            texto_repetido = " ".join(palavra["palavra"].strip() for palavra in palavras[indice:indice + tamanho_grupo])
            cortes_gagueira.append((inicio_primeiro - 0.02, inicio_segundo - 0.02, f"gagueira/repetição: \"{texto_repetido}\""))
            indice += tamanho_grupo
            encontrou = True
            break
        if not encontrou:
            for tamanho_grupo in (4, 3, 2):
                for palavras_soltas in (1, 2, 3):
                    indice_retomada = indice + tamanho_grupo + palavras_soltas
                    if indice_retomada + tamanho_grupo > len(palavras):
                        continue
                    if normalizadas[indice:indice + tamanho_grupo] != normalizadas[indice_retomada:indice_retomada + tamanho_grupo] or not all(normalizadas[indice:indice + tamanho_grupo]):
                        continue
                    ultima_solta = palavras[indice_retomada - 1]["palavra"].strip()
                    if not ultima_solta.endswith(("...", "…", "-")):
                        continue
                    inicio_primeiro = palavras[indice]["inicio"]
                    inicio_retomada = palavras[indice_retomada]["inicio"]
                    if inicio_retomada - inicio_primeiro > 4.0 or ja_removido(inicio_primeiro):
                        continue
                    texto_abandonado = " ".join(palavra["palavra"].strip() for palavra in palavras[indice:indice_retomada])
                    cortes_gagueira.append((inicio_primeiro - 0.02, inicio_retomada - 0.02, f"falso começo: \"{texto_abandonado}\""))
                    indice = indice_retomada
                    encontrou = True
                    break
                if encontrou:
                    break
        if not encontrou:
            indice += 1
    return cortes_gagueira


def carregar_envelope(caminho_audio):
    """Energia da voz em janelas de 10 ms (dB), para encaixar cada corte num respiro de verdade."""
    import subprocess
    import numpy as np
    bruto = subprocess.run(["ffmpeg", "-v", "error", "-i", caminho_audio, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    amostras = np.frombuffer(bruto, dtype=np.float32)
    tamanho_janela = 160
    quantidade = len(amostras) // tamanho_janela
    energia = np.sqrt(np.mean(amostras[:quantidade * tamanho_janela].reshape(quantidade, tamanho_janela) ** 2, axis=1))
    return 20 * np.log10(energia + 1e-9)


def trechos_silenciosos_perto(envelope_db, tempo, janela_busca=0.35, limiar_db=-40.0, duracao_minima=0.12):
    """Respiros (energia abaixo do limiar por pelo menos 120 ms) perto de um instante: lista de (inicio, fim) em segundos."""
    inicio_indice = max(0, int((tempo - janela_busca) * 100))
    fim_indice = min(len(envelope_db), int((tempo + janela_busca) * 100))
    respiros = []
    indice = inicio_indice
    while indice < fim_indice:
        if envelope_db[indice] < limiar_db:
            fim_respiro = indice
            while fim_respiro < len(envelope_db) and envelope_db[fim_respiro] < limiar_db:
                fim_respiro += 1
            comeco_respiro = indice
            while comeco_respiro > 0 and envelope_db[comeco_respiro - 1] < limiar_db:
                comeco_respiro -= 1
            if (fim_respiro - comeco_respiro) / 100 >= duracao_minima:
                respiros.append((comeco_respiro / 100, fim_respiro / 100))
            indice = fim_respiro
        else:
            indice += 1
    return respiros


def encaixar_corte_em_respiros(inicio, fim, envelope_db):
    """O Whisper erra o tempo das palavras perto de hesitações; o corte começa no respiro mais próximo do início
    (depois do fim da fala anterior) e termina no respiro mais próximo do fim (antes da fala seguinte)."""
    respiros_inicio = trechos_silenciosos_perto(envelope_db, inicio)
    if respiros_inicio:
        respiro = min(respiros_inicio, key=lambda par: 0 if par[0] <= inicio <= par[1] else min(abs(par[0] - inicio), abs(par[1] - inicio)))
        inicio = respiro[0] + RESPIRO if not (respiro[0] <= inicio <= respiro[1]) or inicio - respiro[0] < RESPIRO else inicio
    respiros_fim = trechos_silenciosos_perto(envelope_db, fim)
    if respiros_fim:
        respiro = min(respiros_fim, key=lambda par: 0 if par[0] <= fim <= par[1] else min(abs(par[0] - fim), abs(par[1] - fim)))
        fim = respiro[1] - RESPIRO if not (respiro[0] <= fim <= respiro[1]) or respiro[1] - fim < RESPIRO else fim
    return inicio, fim


def unir_intervalos(intervalos):
    ordenados = sorted(intervalos, key=lambda intervalo: intervalo[0])
    unidos = []
    for inicio, fim, motivo in ordenados:
        if unidos and inicio <= unidos[-1][1] + 1e-6:
            if fim > unidos[-1][1]:
                unidos[-1] = (unidos[-1][0], fim, unidos[-1][2] if unidos[-1][2] == motivo else unidos[-1][2] + " + " + motivo)
        else:
            unidos.append((inicio, fim, motivo))
    return unidos


def alinhar_na_grade(tempo):
    return round(tempo * QUADROS_POR_SEGUNDO) / QUADROS_POR_SEGUNDO


def formatar_tempo_srt(segundos):
    milissegundos_totais = int(round(segundos * 1000))
    horas, resto = divmod(milissegundos_totais, 3600000)
    minutos, resto = divmod(resto, 60000)
    segundos_inteiros, milissegundos = divmod(resto, 1000)
    return f"{horas:02d}:{minutos:02d}:{segundos_inteiros:02d},{milissegundos:03d}"


def converter_para_saida(tempo_fonte, mapa):
    for trecho in mapa:
        if trecho["inicio_fonte"] <= tempo_fonte <= trecho["fim_fonte"]:
            return trecho["inicio_saida"] + (tempo_fonte - trecho["inicio_fonte"])
    return None


def aplicar_correcoes_texto(texto, correcoes):
    for errado, certo in correcoes:
        texto = re.sub(errado, certo, texto)
    return texto


def principal():
    caminho_transcricao, caminho_silencios, caminho_decisoes, pasta_saida = sys.argv[1:5]
    palavras = carregar_palavras(caminho_transcricao)
    silencios = carregar_silencios(caminho_silencios)
    decisoes = json.load(open(caminho_decisoes, encoding="utf-8"))
    duracao_bruto = decisoes["duracao_bruto"]
    correcoes_texto = [tuple(par) for par in decisoes.get("correcoes_texto", [])]
    trechos_protegidos = [(trecho["inicio"], trecho["fim"]) for trecho in decisoes.get("manter", [])]

    def esta_protegido(inicio, fim):
        return any(inicio < fim_protegido and fim > inicio_protegido for inicio_protegido, fim_protegido in trechos_protegidos)

    remocoes = [(item["inicio"], item["fim"], item["motivo"] + (" [exato]" if item.get("exato") else "")) for item in decisoes.get("remover", [])]
    palavras_disfluencias = carregar_palavras(sys.argv[5]) if len(sys.argv) > 5 else palavras
    remocoes += detectar_gagueiras(palavras_disfluencias, remocoes)


    # Silêncios a partir de ~0,5 s: sai o miolo, ficam só centésimos de respiro de cada lado.
    # Com o áudio disponível, o silêncio é medido pela energia RMS em janelas de 10 ms (mais fiel que o
    # silencedetect, que quebra o silêncio em qualquer estalo isolado).
    envelope_db = carregar_envelope(sys.argv[6]) if len(sys.argv) > 6 else None
    if envelope_db is not None:
        silencios = []
        indice = 0
        while indice < len(envelope_db):
            if envelope_db[indice] < -40.0:
                fim_indice = indice
                while fim_indice < len(envelope_db) and envelope_db[fim_indice] < -40.0:
                    fim_indice += 1
                if (fim_indice - indice) / 100 > LIMIAR_SILENCIO:
                    silencios.append((indice / 100, fim_indice / 100))
                indice = fim_indice
            else:
                indice += 1
    for inicio_silencio, fim_silencio in silencios:
        if fim_silencio - inicio_silencio <= LIMIAR_SILENCIO:
            continue
        inicio_corte, fim_corte = inicio_silencio + RESPIRO, fim_silencio - RESPIRO
        if inicio_silencio <= 0.01:
            inicio_corte = 0.0
        if fim_silencio >= duracao_bruto - 0.01:
            fim_corte = duracao_bruto
        if esta_protegido(inicio_corte, fim_corte):
            continue
        # O Whisper costuma esticar o começo/fim das palavras para dentro do silêncio; vale a energia medida.
        # Só uma palavra inteira dentro do silêncio (fala muito baixa) impede o corte em volta dela.
        palavras_inteiras_dentro = [palavra for palavra in palavras
                                    if palavra["inicio"] > inicio_silencio + 0.05 and palavra["fim"] < fim_silencio - 0.05 and palavra["fim"] - palavra["inicio"] > 0.12]
        pedacos_removiveis = [(inicio_corte, fim_corte)]
        for palavra in palavras_inteiras_dentro:
            protegido_inicio, protegido_fim = palavra["inicio"] - RESPIRO, palavra["fim"] + RESPIRO
            novos_pedacos = []
            for inicio_pedaco, fim_pedaco in pedacos_removiveis:
                if protegido_fim <= inicio_pedaco or protegido_inicio >= fim_pedaco:
                    novos_pedacos.append((inicio_pedaco, fim_pedaco))
                    continue
                if protegido_inicio > inicio_pedaco:
                    novos_pedacos.append((inicio_pedaco, protegido_inicio))
                if protegido_fim < fim_pedaco:
                    novos_pedacos.append((protegido_fim, fim_pedaco))
            pedacos_removiveis = novos_pedacos
        for inicio_pedaco, fim_pedaco in pedacos_removiveis:
            if fim_pedaco - inicio_pedaco > 0.05:
                remocoes.append((inicio_pedaco, fim_pedaco, f"silêncio de {fim_silencio - inicio_silencio:.1f} s"))

    # Lacunas longas sem nenhuma palavra (ruído de teclado, espera de instalação): o ruído pode ficar acima do
    # limiar de silêncio, então a lacuna vem do Whisper e as bordas são encaixadas no respiro real da voz.
    for palavra_atual, proxima_palavra in zip(palavras_disfluencias, palavras_disfluencias[1:]):
        lacuna = proxima_palavra["inicio"] - palavra_atual["fim"]
        if lacuna <= LACUNA_SEM_FALA:
            continue
        inicio_corte, fim_corte = palavra_atual["fim"] + RESPIRO + 0.05, proxima_palavra["inicio"] - RESPIRO
        if envelope_db is not None:
            # O Whisper costuma marcar o fim da palavra ~0,3 s antes do fim real: o corte só começa numa pausa de
            # verdade (≥ PAUSA_REAL_LACUNA), não numa queda rápida de energia no meio da última sílaba.
            respiros_depois = [par for par in trechos_silenciosos_perto(envelope_db, palavra_atual["fim"], janela_busca=1.0)
                               if par[0] >= palavra_atual["fim"] - 0.3 and par[1] - par[0] >= PAUSA_REAL_LACUNA]
            if respiros_depois:
                inicio_corte = min(respiros_depois)[0] + RESPIRO
            respiros_antes = [par for par in trechos_silenciosos_perto(envelope_db, proxima_palavra["inicio"], janela_busca=1.0)
                              if par[1] <= proxima_palavra["inicio"] + 0.5 and par[1] - par[0] >= PAUSA_REAL_LACUNA]
            if respiros_antes:
                fim_corte = max(respiros_antes, key=lambda par: par[1])[1] - RESPIRO
            # Se a "lacuna" tem energia de voz na maior parte do tempo, a transcrição pulou fala: não corta.
            trecho_envelope = envelope_db[int(inicio_corte * 100):int(fim_corte * 100)]
            if len(trecho_envelope) and (trecho_envelope > -40.0).mean() > FRACAO_MAXIMA_VOZ_NA_LACUNA:
                continue
        if fim_corte - inicio_corte > 0.3 and not esta_protegido(inicio_corte, fim_corte):
            remocoes.append((inicio_corte, fim_corte, f"silêncio/espera sem fala de {lacuna:.1f} s"))
    if palavras and palavras[0]["inicio"] > 1.0:
        remocoes.append((0.0, palavras[0]["inicio"] - RESPIRO, "início antes da primeira fala"))
    if palavras and duracao_bruto - palavras[-1]["fim"] > 1.0:
        remocoes.append((palavras[-1]["fim"] + 0.4, duracao_bruto, "fim depois da última fala"))

    if envelope_db is not None:
        remocoes_encaixadas = []
        for inicio, fim, motivo in remocoes:
            if not motivo.startswith("silêncio") and not motivo.endswith("[exato]"):
                inicio, fim = encaixar_corte_em_respiros(inicio, fim, envelope_db)
            motivo = motivo.replace(" [exato]", "")
            if fim - inicio > 0.05:
                remocoes_encaixadas.append((inicio, fim, motivo))
        remocoes = remocoes_encaixadas

    remocoes_unidas = unir_intervalos([(max(0.0, inicio), min(duracao_bruto, fim), motivo) for inicio, fim, motivo in remocoes if fim - inicio > 0.02])

    trechos_mantidos = []
    cursor = 0.0
    for inicio, fim, _ in remocoes_unidas:
        if inicio > cursor:
            trechos_mantidos.append((cursor, inicio))
        cursor = max(cursor, fim)
    if cursor < duracao_bruto:
        trechos_mantidos.append((cursor, duracao_bruto))
    trechos_alinhados = []
    for inicio, fim in trechos_mantidos:
        inicio_alinhado, fim_alinhado = alinhar_na_grade(inicio), alinhar_na_grade(fim)
        if fim_alinhado - inicio_alinhado >= 2 / QUADROS_POR_SEGUNDO:
            trechos_alinhados.append((inicio_alinhado, fim_alinhado))

    mapa = []
    tempo_saida = 0.0
    for inicio, fim in trechos_alinhados:
        mapa.append({"inicio_fonte": round(inicio, 4), "fim_fonte": round(fim, 4), "inicio_saida": round(tempo_saida, 4)})
        tempo_saida += fim - inicio

    with open(f"{pasta_saida}/cortes.csv", "w", newline="", encoding="utf-8-sig") as arquivo_csv:
        escritor = csv.writer(arquivo_csv, delimiter=";")
        escritor.writerow(["inicio_bruto", "fim_bruto", "duracao_s", "motivo", "trecho_da_transcricao"])
        for inicio, fim, motivo in remocoes_unidas:
            escritor.writerow([formatar_tempo_srt(inicio).replace(",", "."), formatar_tempo_srt(fim).replace(",", "."), f"{fim - inicio:.2f}".replace(".", ","),
                               motivo, aplicar_correcoes_texto(trecho_da_transcricao(palavras, inicio, fim), correcoes_texto)])
    json.dump([[inicio, fim] for inicio, fim in trechos_alinhados], open(f"{pasta_saida}/trechos_mantidos.json", "w"))
    json.dump(mapa, open(f"{pasta_saida}/mapa_tempo.json", "w"), indent=1)

    # Legenda SRT no tempo editado: agrupa palavras mantidas em blocos de até ~42 caracteres / 5 s.
    palavras_mantidas = []
    for palavra in palavras_disfluencias:
        melhor_sobreposicao = None
        for trecho in mapa:
            inicio_sobreposto = max(palavra["inicio"], trecho["inicio_fonte"])
            fim_sobreposto = min(palavra["fim"], trecho["fim_fonte"])
            if fim_sobreposto > inicio_sobreposto and (melhor_sobreposicao is None or fim_sobreposto - inicio_sobreposto > melhor_sobreposicao[1] - melhor_sobreposicao[0]):
                melhor_sobreposicao = (inicio_sobreposto, fim_sobreposto, trecho)
        if melhor_sobreposicao is None:
            continue
        inicio_sobreposto, fim_sobreposto, trecho = melhor_sobreposicao
        duracao_palavra = max(palavra["fim"] - palavra["inicio"], 1e-3)
        if fim_sobreposto - inicio_sobreposto < min(0.08, 0.4 * duracao_palavra):
            continue
        palavras_mantidas.append({"inicio": trecho["inicio_saida"] + (inicio_sobreposto - trecho["inicio_fonte"]),
                                  "fim": trecho["inicio_saida"] + (fim_sobreposto - trecho["inicio_fonte"]), "texto": palavra["palavra"].strip()})
    blocos_legenda = []
    bloco_atual = []
    for palavra in palavras_mantidas:
        texto_bloco = " ".join(item["texto"] for item in bloco_atual + [palavra])
        quebra = bloco_atual and (len(texto_bloco) > 42 or palavra["fim"] - bloco_atual[0]["inicio"] > 5 or palavra["inicio"] - bloco_atual[-1]["fim"] > 0.7)
        if quebra:
            blocos_legenda.append(bloco_atual)
            bloco_atual = []
        bloco_atual.append(palavra)
        if palavra["texto"].endswith((".", "?", "!")) and len(" ".join(item["texto"] for item in bloco_atual)) > 18:
            blocos_legenda.append(bloco_atual)
            bloco_atual = []
    if bloco_atual:
        blocos_legenda.append(bloco_atual)
    with open(f"{pasta_saida}/legenda.srt", "w", encoding="utf-8") as arquivo_srt:
        for numero, bloco in enumerate(blocos_legenda, start=1):
            texto = aplicar_correcoes_texto(" ".join(item["texto"] for item in bloco), correcoes_texto)
            arquivo_srt.write(f"{numero}\n{formatar_tempo_srt(bloco[0]['inicio'])} --> {formatar_tempo_srt(bloco[-1]['fim'])}\n{texto}\n\n")
    with open(f"{pasta_saida}/transcricao_editada.txt", "w", encoding="utf-8") as arquivo_texto:
        for bloco in blocos_legenda:
            texto = aplicar_correcoes_texto(" ".join(item["texto"] for item in bloco), correcoes_texto)
            arquivo_texto.write(f"[{bloco[0]['inicio']:7.1f}] {texto}\n")

    tempo_removido = sum(fim - inicio for inicio, fim, _ in remocoes_unidas)
    print(f"bruto {duracao_bruto / 60:.1f} min | removido {tempo_removido / 60:.1f} min em {len(remocoes_unidas)} cortes | final {tempo_saida / 60:.1f} min | {len(trechos_alinhados)} trechos")


if __name__ == "__main__":
    principal()
