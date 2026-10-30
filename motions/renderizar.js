// Renderiza motions do motor.html em WebM VP9 com transparência (yuva420p), 1920x1080, 30 fps.
// Uso: node renderizar.js <arquivo_especificacoes.json> <pasta_saida> [--previa] [--so=nome1,nome2] [--identidade=config_editor.json]
//   --previa: em vez do vídeo, salva 6 quadros-chave PNG de cada motion para folha de contato.
//   --so: renderiza só os motions com esses nomes.
//   --identidade: lê "motions.marca_dagua", "motions.cor_destaque" e "motions.cor_fundo" do config_editor.json da pasta de edição.
//   Imagens ("src") podem ser caminhos absolutos do computador: viram file:// automaticamente.
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");

const caminhoEspecificacoes = process.argv[2];
const pastaSaida = process.argv[3];
const modoPrevia = process.argv.includes("--previa");
const filtroNomes = process.argv.filter((argumento) => argumento.startsWith("--so=")).map((argumento) => argumento.slice(5).split(",")).flat();
const argumentoIdentidade = process.argv.find((argumento) => argumento.startsWith("--identidade="));

function lerIdentidade() {
  if (!argumentoIdentidade) return null;
  const configuracao = JSON.parse(fs.readFileSync(argumentoIdentidade.slice(13), "utf8"));
  return configuracao.motions || null;
}

function hexParaRgb(corHex) {
  const valor = corHex.replace("#", "");
  return [0, 2, 4].map((posicao) => parseInt(valor.slice(posicao, posicao + 2), 16)).join(" ");
}

function ajustarCaminhoDaImagem(especificacao) {
  if (!especificacao.src) return especificacao;
  const ehCaminhoAbsoluto = path.isAbsolute(especificacao.src) && fs.existsSync(especificacao.src);
  return ehCaminhoAbsoluto ? { ...especificacao, src: pathToFileURL(especificacao.src).href } : especificacao;
}

function codificarWebmComAlfa(caminhoVideo) {
  const processoFfmpeg = spawn("ffmpeg", [
    "-y", "-hide_banner", "-loglevel", "error",
    "-f", "image2pipe", "-framerate", "30", "-c:v", "png", "-i", "-",
    "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "30", "-deadline", "good", "-cpu-used", "4", "-row-mt", "1",
    "-auto-alt-ref", "0", caminhoVideo,
  ], { stdio: ["pipe", "inherit", "inherit"] });
  return processoFfmpeg;
}

function escreverNoFluxo(fluxo, dados) {
  return new Promise((resolver) => { if (fluxo.write(dados)) resolver(); else fluxo.once("drain", resolver); });
}

(async () => {
  const especificacoes = JSON.parse(fs.readFileSync(caminhoEspecificacoes, "utf8"));
  fs.mkdirSync(pastaSaida, { recursive: true });
  const navegador = await chromium.launch();
  const pagina = await navegador.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const enderecoMotor = pathToFileURL(path.resolve(__dirname, "motor.html")).href;
  const identidade = lerIdentidade();

  for (const especificacao of especificacoes) {
    if (filtroNomes.length && !filtroNomes.includes(especificacao.nome)) continue;
    await pagina.goto(enderecoMotor);
    if (identidade) {
      await pagina.evaluate((dados) => {
        if (dados.marcaDagua) window.MARCA_DAGUA = dados.marcaDagua;
        if (dados.corDestaque) {
          document.documentElement.style.setProperty("--cor-destaque", dados.corDestaque);
          document.documentElement.style.setProperty("--cor-destaque-rgb", dados.corDestaqueRgb);
        }
        if (dados.corFundo) document.documentElement.style.setProperty("--cor-fundo", dados.corFundo);
      }, { marcaDagua: identidade.marca_dagua, corDestaque: identidade.cor_destaque, corDestaqueRgb: identidade.cor_destaque ? hexParaRgb(identidade.cor_destaque) : null, corFundo: identidade.cor_fundo });
    }
    const totalQuadros = await pagina.evaluate((dados) => window.prepararMotion(dados), ajustarCaminhoDaImagem(especificacao));
    const inicio = Date.now();
    if (modoPrevia) {
      const quadrosChave = [0.12, 0.3, 0.5, 0.7, 0.85, 0.97].map((fracao) => Math.min(totalQuadros - 1, Math.round(totalQuadros * fracao)));
      for (const [indice, quadro] of quadrosChave.entries()) {
        await pagina.evaluate((numero) => window.desenharQuadro(numero), quadro);
        await pagina.screenshot({ path: path.join(pastaSaida, `${especificacao.nome}_${indice}.png`), omitBackground: true });
      }
    } else {
      const caminhoVideo = path.join(pastaSaida, `${especificacao.nome}.webm`);
      const processoFfmpeg = codificarWebmComAlfa(caminhoVideo);
      const terminou = new Promise((resolver, rejeitar) => processoFfmpeg.on("close", (codigo) => (codigo === 0 ? resolver() : rejeitar(new Error("ffmpeg saiu com código " + codigo)))));
      for (let quadro = 0; quadro < totalQuadros; quadro++) {
        await pagina.evaluate((numero) => window.desenharQuadro(numero), quadro);
        const imagem = await pagina.screenshot({ omitBackground: true, type: "png" });
        await escreverNoFluxo(processoFfmpeg.stdin, imagem);
      }
      processoFfmpeg.stdin.end();
      await terminou;
    }
    console.log(`${especificacao.nome}: ${totalQuadros} quadros em ${((Date.now() - inicio) / 1000).toFixed(1)}s`);
  }
  await navegador.close();
})().catch((erro) => { console.error(erro); process.exit(1); });
