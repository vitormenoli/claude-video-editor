// Renderiza motions do motor.html em WebM VP9 com transparência (yuva420p), 1920x1080, 30 fps.
// Uso: node renderizar.js <arquivo_especificacoes.json> <pasta_saida> [--previa]
//   --previa: em vez do vídeo, salva 6 quadros-chave PNG de cada motion para folha de contato.
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const caminhoEspecificacoes = process.argv[2];
const pastaSaida = process.argv[3];
const modoPrevia = process.argv.includes("--previa");
const filtroNomes = process.argv.filter((argumento) => argumento.startsWith("--so=")).map((argumento) => argumento.slice(5).split(",")).flat();

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
  const enderecoMotor = "file://" + path.resolve(__dirname, "motor.html");

  for (const especificacao of especificacoes) {
    if (filtroNomes.length && !filtroNomes.includes(especificacao.nome)) continue;
    await pagina.goto(enderecoMotor);
    const totalQuadros = await pagina.evaluate((dados) => window.prepararMotion(dados), especificacao);
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
