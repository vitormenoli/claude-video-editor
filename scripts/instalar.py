"""Confere e instala tudo o que a skill precisa, e diz exatamente o que falta quando algo não dá para instalar sozinho.

Instala sozinho: pacotes Python (requirements.txt), Playwright (npm install) e o Chromium do Playwright.
Só confere e explica como instalar (precisa do usuário/administrador): Python, FFmpeg com libx264 e libvpx-vp9, Node.js.

Uso: python3 instalar.py [--baixar-modelo=large-v3] [--so-conferir]
  --baixar-modelo: já baixa o modelo do Whisper (o large-v3 tem ~3 GB), para não esperar na primeira edição.
  --so-conferir: não instala nada, só mostra o que está ok e o que falta.
Sai com código 0 quando está tudo pronto e 1 quando falta algo.
"""
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

PASTA_DA_SKILL = Path(__file__).resolve().parent.parent
VERSAO_MINIMA_PYTHON = (3, 10)
VERSAO_MINIMA_NODE = 18

COMO_INSTALAR = {
    "python": {"Windows": "winget install Python.Python.3.12", "Darwin": "brew install python@3.12", "Linux": "sudo apt install python3 python3-pip"},
    "ffmpeg": {"Windows": "winget install Gyan.FFmpeg", "Darwin": "brew install ffmpeg", "Linux": "sudo apt install ffmpeg"},
    "node": {"Windows": "winget install OpenJS.NodeJS.LTS", "Darwin": "brew install node", "Linux": "sudo apt install nodejs npm (ou use o nvm para ter a versão 18+)"},
}


def comando_de_instalacao(programa):
    return COMO_INSTALAR[programa].get(platform.system(), COMO_INSTALAR[programa]["Linux"])


def rodar(comando, pasta=None):
    resultado = subprocess.run(comando, cwd=pasta, capture_output=True, text=True)
    return resultado.returncode, (resultado.stdout or "") + (resultado.stderr or "")


def conferir_python(problemas):
    versao = sys.version_info[:3]
    if versao[:2] < VERSAO_MINIMA_PYTHON:
        problemas.append(f"Python {versao[0]}.{versao[1]} é antigo (precisa de 3.10+). Instale: {comando_de_instalacao('python')}")
        return
    print(f"[ok] Python {versao[0]}.{versao[1]}.{versao[2]}")


def conferir_ffmpeg(problemas):
    caminho_ffmpeg = shutil.which("ffmpeg")
    caminho_ffprobe = shutil.which("ffprobe")
    if not caminho_ffmpeg or not caminho_ffprobe:
        problemas.append(f"FFmpeg/ffprobe não encontrado no PATH. Instale: {comando_de_instalacao('ffmpeg')} (depois feche e abra o terminal)")
        return
    _, saida_versao = rodar([caminho_ffmpeg, "-version"])
    primeira_linha = saida_versao.splitlines()[0] if saida_versao else "versão desconhecida"
    _, codificadores = rodar([caminho_ffmpeg, "-hide_banner", "-encoders"])
    _, decodificadores = rodar([caminho_ffmpeg, "-hide_banner", "-decoders"])
    faltando = []
    if "libx264" not in codificadores:
        faltando.append("codificador libx264")
    if "libvpx-vp9" not in codificadores:
        faltando.append("codificador libvpx-vp9")
    if "libvpx-vp9" not in decodificadores:
        faltando.append("decodificador libvpx-vp9 (motions com transparência)")
    if faltando:
        problemas.append(f"O FFmpeg instalado não tem: {', '.join(faltando)}. Instale uma versão completa: {comando_de_instalacao('ffmpeg')}")
        return
    print(f"[ok] {primeira_linha}")


def conferir_node(problemas):
    caminho_node = shutil.which("node")
    caminho_npm = shutil.which("npm")
    if not caminho_node or not caminho_npm:
        problemas.append(f"Node.js/npm não encontrado. Instale: {comando_de_instalacao('node')}")
        return None
    _, versao = rodar([caminho_node, "--version"])
    numero_principal = int(re.search(r"v(\d+)", versao).group(1)) if re.search(r"v(\d+)", versao) else 0
    if numero_principal < VERSAO_MINIMA_NODE:
        problemas.append(f"Node {versao.strip()} é antigo (precisa de 18+). Instale: {comando_de_instalacao('node')}")
        return None
    print(f"[ok] Node {versao.strip()}")
    return caminho_npm


def instalar_pacotes_python(problemas, so_conferir):
    arquivo_requisitos = PASTA_DA_SKILL / "requirements.txt"
    faltando = []
    for modulo in ("faster_whisper", "numpy", "PIL"):
        codigo, _ = rodar([sys.executable, "-c", f"import {modulo}"])
        if codigo != 0:
            faltando.append(modulo)
    if not faltando:
        print("[ok] pacotes Python (faster-whisper, numpy, Pillow)")
        return
    if so_conferir:
        problemas.append(f"Faltam pacotes Python: {', '.join(faltando)}. Rode: {sys.executable} -m pip install -r \"{arquivo_requisitos}\"")
        return
    print(f"[instalando] pacotes Python: {', '.join(faltando)}")
    codigo, saida = rodar([sys.executable, "-m", "pip", "install", "-r", str(arquivo_requisitos)])
    if codigo != 0 and "externally-managed-environment" in saida:
        codigo, saida = rodar([sys.executable, "-m", "pip", "install", "--break-system-packages", "-r", str(arquivo_requisitos)])
    if codigo != 0:
        problemas.append("Não consegui instalar os pacotes Python. Últimas linhas do erro:\n" + "\n".join(saida.strip().splitlines()[-8:]))
        return
    print("[ok] pacotes Python instalados")


VERIFICAR_PLAYWRIGHT = ("let playwright; try { playwright = require('playwright'); } catch (erro) { process.exit(3); } "
                       "process.exit(require('fs').existsSync(playwright.chromium.executablePath()) ? 0 : 2);")


def situacao_do_playwright():
    """0 = Playwright e Chromium prontos; 2 = falta o Chromium; 3 = falta o pacote playwright."""
    codigo, _ = rodar(["node", "-e", VERIFICAR_PLAYWRIGHT], pasta=str(PASTA_DA_SKILL))
    return codigo


def instalar_playwright(caminho_npm, problemas, so_conferir):
    situacao = situacao_do_playwright()
    if situacao == 0:
        print("[ok] Playwright + Chromium")
        return
    if so_conferir:
        falta = "o pacote playwright e o Chromium" if situacao == 3 else "o Chromium do Playwright"
        problemas.append(f"Falta {falta}. Rode na pasta da skill: npm install && npx playwright install chromium")
        return
    if situacao == 3:
        print("[instalando] Playwright (npm install)")
        codigo, saida = rodar([caminho_npm, "install"], pasta=str(PASTA_DA_SKILL))
        if codigo != 0:
            problemas.append("npm install falhou. Últimas linhas do erro:\n" + "\n".join(saida.strip().splitlines()[-8:]))
            return
    if situacao_do_playwright() == 0:
        print("[ok] Playwright + Chromium")
        return
    caminho_npx = shutil.which("npx")
    if not caminho_npx:
        problemas.append("npx não encontrado (vem junto com o Node.js). Reinstale o Node.js.")
        return
    print("[instalando] Chromium do Playwright (pode demorar na primeira vez)")
    codigo, saida = rodar([caminho_npx, "playwright", "install", "chromium"], pasta=str(PASTA_DA_SKILL))
    if codigo != 0 or situacao_do_playwright() != 0:
        problemas.append("Não consegui instalar o Chromium do Playwright. Últimas linhas do erro:\n" + "\n".join(saida.strip().splitlines()[-8:]))
        return
    print("[ok] Playwright + Chromium")


def baixar_modelo_whisper(nome_modelo, problemas):
    print(f"[baixando] modelo do Whisper {nome_modelo} (só na primeira vez)")
    codigo, saida = rodar([sys.executable, "-c", f"from faster_whisper import WhisperModel; WhisperModel('{nome_modelo}', device='cpu', compute_type='int8')"])
    if codigo != 0:
        problemas.append(f"Não consegui baixar o modelo {nome_modelo}. Últimas linhas do erro:\n" + "\n".join(saida.strip().splitlines()[-8:]))
        return
    print(f"[ok] modelo {nome_modelo} pronto")


def principal():
    so_conferir = "--so-conferir" in sys.argv
    modelo_para_baixar = next((argumento.split("=", 1)[1] for argumento in sys.argv if argumento.startswith("--baixar-modelo=")), None)
    problemas = []
    print(f"Skill em: {PASTA_DA_SKILL}  ·  sistema: {platform.system()} {platform.machine()}")
    conferir_python(problemas)
    conferir_ffmpeg(problemas)
    caminho_npm = conferir_node(problemas)
    instalar_pacotes_python(problemas, so_conferir)
    if caminho_npm:
        instalar_playwright(caminho_npm, problemas, so_conferir)
    if modelo_para_baixar and not so_conferir and not any("pacotes Python" in problema for problema in problemas):
        baixar_modelo_whisper(modelo_para_baixar, problemas)
    if problemas:
        print("\nFALTA RESOLVER:")
        for numero, problema in enumerate(problemas, start=1):
            print(f"{numero}. {problema}")
        sys.exit(1)
    print("\nTudo pronto para editar.")


if __name__ == "__main__":
    principal()
