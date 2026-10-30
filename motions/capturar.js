// Captura um print real de um site ou repositório oficial (para logos e páginas de outras marcas: nunca redesenhar).
// Uso: node capturar.js <url> <arquivo_saida.png> [seletor_css_de_um_elemento]
//   Sem seletor: print da área visível da página (1440x1000, densidade 2x, tema escuro).
//   Com seletor: print só daquele elemento (ex.: "article img" para a imagem do README no GitHub).
const { chromium } = require("playwright");

const enderecoDaPagina = process.argv[2];
const caminhoDoPrint = process.argv[3];
const seletorDoElemento = process.argv[4];

(async () => {
  if (!enderecoDaPagina || !caminhoDoPrint) {
    console.error("Uso: node capturar.js <url> <arquivo_saida.png> [seletor_css]");
    process.exit(1);
  }
  const navegador = await chromium.launch();
  const pagina = await navegador.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2, colorScheme: "dark" });
  await pagina.goto(enderecoDaPagina, { waitUntil: "domcontentloaded", timeout: 45000 });
  await pagina.waitForTimeout(3000);
  if (seletorDoElemento) {
    const elemento = await pagina.$(seletorDoElemento);
    if (!elemento) {
      console.error("Elemento não encontrado:", seletorDoElemento);
      await navegador.close();
      process.exit(1);
    }
    await elemento.screenshot({ path: caminhoDoPrint });
  } else {
    await pagina.screenshot({ path: caminhoDoPrint });
  }
  console.log("print salvo em", caminhoDoPrint);
  await navegador.close();
})().catch((erro) => { console.error(erro.message); process.exit(1); });
