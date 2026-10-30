"""Prepara a pasta de edição escolhida pelo usuário: cria as subpastas, os arquivos de instrução e o config_editor.json.

Estrutura criada:
  Arquivos Brutos/     o usuário coloca aqui o vídeo bruto (um só, ou "Parte 1.mp4", "Parte 2.mp4"...) e o roteiro (.md ou .txt)
  Midia do Canal/      música de fundo, encerramento e logo do canal (opcionais)
  Resultado Final/     o vídeo editado, a legenda, os capítulos e a descrição (e as prévias, se ativadas)
  _edicao/             arquivos de trabalho (pode apagar depois que o vídeo for publicado)
  config_editor.json   configurações escolhidas na instalação (duração, prévias, música, identidade visual...)
  folha_de_estilo.md   regras de edição do canal (começa com o modelo da skill; o usuário pode editar)

Uso: python3 configurar_pasta.py <pasta_de_edicao> [--config='{"duracao_minima_min": 8, ...}'] [--config-arquivo=respostas.json]
Rodar de novo é seguro: não apaga nada, só cria o que falta e atualiza as configurações passadas.
"""
import json
import shutil
import sys
from pathlib import Path

PASTA_DA_SKILL = Path(__file__).resolve().parent.parent
NOME_PASTA_BRUTOS = "Arquivos Brutos"
NOME_PASTA_MIDIA = "Midia do Canal"
NOME_PASTA_RESULTADO = "Resultado Final"
NOME_PASTA_TRABALHO = "_edicao"

CONFIGURACAO_PADRAO = {
    "versao": 1,
    "idioma": "pt",
    "modelo_whisper": "large-v3",
    "duracao_minima_min": 8,
    "duracao_maxima_min": 15,
    "previas": True,
    "previa_inicio_s": 60,
    "previa_fim_s": 30,
    "silencio_minimo_s": 0.45,
    "respiro_s": 0.08,
    "voz_alvo_lufs": -14.0,
    "voz_pico_dbtp": -1.5,
    "musica_de_fundo": "Midia do Canal/musica_fundo.mp3",
    "musica_alvo_lufs": -40.0,
    "ducking_db": -8.0,
    "encerramento": "Midia do Canal/encerramento.mp4",
    "crossfade_final_s": 0.5,
    "efeitos_sonoros": True,
    "efeitos_ganho_db": -24.0,
    "quantidade_de_motions": "normal",
    "legenda_srt": True,
    "capitulos": True,
    "descricao_youtube": True,
    "motions": {
        "marca_dagua": "",
        "cor_destaque": "#4F8CFF",
        "cor_fundo": "#0F1115"
    }
}

LEIA_ME_BRUTOS = """COMO USAR ESTA PASTA

1. Coloque aqui o vídeo bruto (gravação de tela + voz).
   - Um vídeo só: qualquer nome (ex.: "gravacao.mp4").
   - Gravou em partes? Nomeie na ordem: "Parte 1.mp4", "Parte 2.mp4", "Parte 3.mp4"...
     Elas são juntadas nessa ordem antes da edição.
   - Não deixe outros vídeos aqui junto.

2. Coloque o roteiro do vídeo num arquivo .md ou .txt (ex.: "roteiro.md"), com:
   - título do vídeo;
   - descrição para o YouTube (se tiver);
   - os blocos/assuntos na ordem (viram os capítulos);
   - links citados no vídeo;
   - o que NÃO pode aparecer na tela (vai desfocado).

3. Peça ao Claude: "edita o vídeo da pasta Arquivos Brutos".
O resultado sai na pasta "Resultado Final".
"""

LEIA_ME_MIDIA = """MÍDIA DO CANAL (opcional)

- musica_fundo.mp3   música de fundo sem direitos autorais (entra bem baixa, com ducking quando você fala)
- encerramento.mp4   vinheta/logo animada que vai no final do vídeo, com crossfade
- logo.png           logo do canal

Use nomes sem acento. Para trocar os nomes ou desligar a música/encerramento, edite o config_editor.json
(campos "musica_de_fundo" e "encerramento"; use null para não usar).
"""


def mesclar_configuracao(base, novos_valores):
    resultado = dict(base)
    for chave, valor in novos_valores.items():
        if isinstance(valor, dict) and isinstance(resultado.get(chave), dict):
            resultado[chave] = mesclar_configuracao(resultado[chave], valor)
        else:
            resultado[chave] = valor
    return resultado


def principal():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    pasta_edicao = Path(sys.argv[1]).expanduser().resolve()
    respostas = {}
    for argumento in sys.argv[2:]:
        if argumento.startswith("--config="):
            respostas = mesclar_configuracao(respostas, json.loads(argumento[len("--config="):]))
        if argumento.startswith("--config-arquivo="):
            respostas = mesclar_configuracao(respostas, json.load(open(argumento[len("--config-arquivo="):], encoding="utf-8")))

    for nome_pasta in (NOME_PASTA_BRUTOS, NOME_PASTA_MIDIA, NOME_PASTA_RESULTADO, NOME_PASTA_TRABALHO):
        (pasta_edicao / nome_pasta).mkdir(parents=True, exist_ok=True)
    (pasta_edicao / NOME_PASTA_BRUTOS / "LEIA-ME.txt").write_text(LEIA_ME_BRUTOS, encoding="utf-8")
    (pasta_edicao / NOME_PASTA_MIDIA / "LEIA-ME.txt").write_text(LEIA_ME_MIDIA, encoding="utf-8")

    caminho_configuracao = pasta_edicao / "config_editor.json"
    configuracao_atual = json.load(open(caminho_configuracao, encoding="utf-8")) if caminho_configuracao.exists() else {}
    configuracao_final = mesclar_configuracao(mesclar_configuracao(CONFIGURACAO_PADRAO, configuracao_atual), respostas)
    caminho_configuracao.write_text(json.dumps(configuracao_final, ensure_ascii=False, indent=2), encoding="utf-8")

    caminho_folha = pasta_edicao / "folha_de_estilo.md"
    if not caminho_folha.exists():
        shutil.copy(PASTA_DA_SKILL / "referencias" / "folha_de_estilo_modelo.md", caminho_folha)

    print(f"Pasta de edição pronta: {pasta_edicao}")
    for nome_pasta in (NOME_PASTA_BRUTOS, NOME_PASTA_MIDIA, NOME_PASTA_RESULTADO, NOME_PASTA_TRABALHO):
        print(f"  {nome_pasta}/")
    print("  config_editor.json")
    print("  folha_de_estilo.md")
    print(json.dumps(configuracao_final, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    principal()
