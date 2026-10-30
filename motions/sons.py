"""Sintetiza os efeitos sonoros dos motions (originais, sem direitos autorais), 48 kHz estéreo, semente fixa."""
import sys
import wave
import numpy as np

TAXA_AMOSTRAGEM = 48000
gerador_aleatorio = np.random.default_rng(1234)


def salvar_wav(caminho, amostras_mono):
    amostras_mono = amostras_mono / (np.max(np.abs(amostras_mono)) + 1e-9) * 0.7
    estereo = np.stack([amostras_mono, amostras_mono], axis=1)
    inteiros = (estereo * 32767).astype(np.int16)
    with wave.open(caminho, "wb") as arquivo:
        arquivo.setnchannels(2)
        arquivo.setsampwidth(2)
        arquivo.setframerate(TAXA_AMOSTRAGEM)
        arquivo.writeframes(inteiros.tobytes())


def envelope_exponencial(numero_amostras, tempo_ataque, tempo_decaimento):
    tempos = np.arange(numero_amostras) / TAXA_AMOSTRAGEM
    ataque = np.clip(tempos / max(tempo_ataque, 1e-6), 0, 1)
    decaimento = np.exp(-np.maximum(tempos - tempo_ataque, 0) / tempo_decaimento)
    return ataque * decaimento


def filtro_passa_baixa_simples(sinal, frequencia_corte):
    coeficiente = np.exp(-2 * np.pi * frequencia_corte / TAXA_AMOSTRAGEM)
    saida = np.zeros_like(sinal)
    acumulado = 0.0
    for indice, valor in enumerate(sinal):
        acumulado = (1 - coeficiente) * valor + coeficiente * acumulado
        saida[indice] = acumulado
    return saida


def som_pop(duracao=0.12):
    """Bolha curta e macia para entrada de pílula/etiqueta."""
    numero_amostras = int(duracao * TAXA_AMOSTRAGEM)
    tempos = np.arange(numero_amostras) / TAXA_AMOSTRAGEM
    frequencia = 520 + 380 * np.exp(-tempos / 0.025)
    fase = 2 * np.pi * np.cumsum(frequencia) / TAXA_AMOSTRAGEM
    return np.sin(fase) * envelope_exponencial(numero_amostras, 0.004, 0.035)


def som_sopro(duracao=0.42):
    """Whoosh suave de ruído filtrado para transição e entrada de painel."""
    numero_amostras = int(duracao * TAXA_AMOSTRAGEM)
    ruido = gerador_aleatorio.normal(0, 1, numero_amostras)
    progresso = np.linspace(0, 1, numero_amostras)
    sinal_filtrado = np.zeros(numero_amostras)
    acumulado = 0.0
    for indice in range(numero_amostras):
        frequencia_corte = 300 + 2200 * np.sin(np.pi * progresso[indice]) ** 2
        coeficiente = np.exp(-2 * np.pi * frequencia_corte / TAXA_AMOSTRAGEM)
        acumulado = (1 - coeficiente) * ruido[indice] + coeficiente * acumulado
        sinal_filtrado[indice] = acumulado
    envelope = np.sin(np.pi * progresso) ** 1.6
    return sinal_filtrado * envelope


def som_tique(duracao=0.03):
    """Tique seco e curto, usado em sequência no contador."""
    numero_amostras = int(duracao * TAXA_AMOSTRAGEM)
    tempos = np.arange(numero_amostras) / TAXA_AMOSTRAGEM
    return np.sin(2 * np.pi * 1800 * tempos) * envelope_exponencial(numero_amostras, 0.001, 0.006)


def som_contador(duracao=1.3, quantidade_tiques=16):
    """Tiques desacelerando, acompanhando o número que sobe e para."""
    numero_amostras = int(duracao * TAXA_AMOSTRAGEM)
    sinal = np.zeros(numero_amostras)
    tique = som_tique()
    for indice in range(quantidade_tiques):
        fracao = indice / quantidade_tiques
        posicao_relativa = 1 - (1 - fracao) ** 0.5
        inicio = int(posicao_relativa * (numero_amostras - len(tique)))
        sinal[inicio:inicio + len(tique)] += tique * (0.6 + 0.4 * (1 - fracao))
    return sinal


def som_digitacao(duracao=1.2, quantidade_teclas=18):
    """Cliques de teclado macios para comando sendo digitado."""
    numero_amostras = int(duracao * TAXA_AMOSTRAGEM)
    sinal = np.zeros(numero_amostras)
    tamanho_clique = int(0.018 * TAXA_AMOSTRAGEM)
    for indice in range(quantidade_teclas):
        inicio = int((indice + gerador_aleatorio.uniform(-0.3, 0.3)) / quantidade_teclas * (numero_amostras - tamanho_clique))
        inicio = max(0, min(numero_amostras - tamanho_clique, inicio))
        ruido = gerador_aleatorio.normal(0, 1, tamanho_clique)
        clique = filtro_passa_baixa_simples(ruido, 3500) * envelope_exponencial(tamanho_clique, 0.0005, 0.004)
        sinal[inicio:inicio + tamanho_clique] += clique * gerador_aleatorio.uniform(0.6, 1.0)
    return sinal


def som_impacto_suave(duracao=0.5):
    """Batida grave e curta para o resultado do teste (sem estouro)."""
    numero_amostras = int(duracao * TAXA_AMOSTRAGEM)
    tempos = np.arange(numero_amostras) / TAXA_AMOSTRAGEM
    frequencia = 70 + 90 * np.exp(-tempos / 0.04)
    fase = 2 * np.pi * np.cumsum(frequencia) / TAXA_AMOSTRAGEM
    corpo = np.sin(fase) * envelope_exponencial(numero_amostras, 0.003, 0.14)
    brilho = som_pop(0.12)
    corpo[:len(brilho)] += brilho * 0.35
    return corpo


if __name__ == "__main__":
    pasta_saida = sys.argv[1]
    salvar_wav(f"{pasta_saida}/sfx_pop.wav", som_pop())
    salvar_wav(f"{pasta_saida}/sfx_sopro.wav", som_sopro())
    salvar_wav(f"{pasta_saida}/sfx_contador.wav", som_contador())
    salvar_wav(f"{pasta_saida}/sfx_digitacao.wav", som_digitacao())
    salvar_wav(f"{pasta_saida}/sfx_impacto.wav", som_impacto_suave())
    print("efeitos sonoros gerados")
