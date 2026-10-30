# Modelos de motion (`motions/motor.html`)

Todo motion é um objeto dentro de `"motion"` no `roteiro_motions.json`, com `tipo` e `duracao` (segundos) obrigatórios.
Coordenadas em pixels de um quadro 1920x1080. Em títulos e legendas, `*palavra*` fica verde.
Cores de destaque nos itens: `"cor": "amarelo"` (dúvida) e `"cor": "vermelho"` (alerta).

| Tipo | Como aparece no vídeo | Parâmetros |
|---|---|---|
| `abertura` | Cartão com o título do vídeo, sobre a tela, nos primeiros segundos | `x`, `y`, `largura`, `rotulo`, `linhas` (lista), `tamanhoTitulo`, `pilulas` (lista) |
| `capitulo` | Título de capítulo discreto no canto ("02 / 09 · O que é") | `x`, `y`, `numero`, `titulo` |
| `transicao` | Linha verde varrendo a tela + escurecimento rápido (0,4 s) | `intensidade` (0 a 1) |
| `pilula` | Etiqueta pequena (comando, ferramenta, número, aviso) | `x`, `y`, `texto`, `rotulo` (texto pequeno acima), `alinhamento: "direita"` (o `x` vira a borda direita) |
| `comando` | Janela de terminal com o comando sendo digitado | `x`, `y`, `largura`, `comando`, `tituloJanela`, `prompt`, `tamanhoFonte`, `duracaoDigitacao`, `destaqueFinal`, `aviso`, `avisoAcima` |
| `painel` | Título + itens que entram um a um; tela cheia ou à esquerda da tela gravada | `linhas`, `rotulo`, `itens`, `layout: "dividido"`, `topo`, `tamanhoTitulo`, `itensEmColuna`, `semFundoAnimado` |
| `comparacao` | Dois números lado a lado com barras e contagem (resultado de teste) | `titulo`, `subtitulo`, `lados` (2 objetos), `delta`, `deltaNegativo`, `fonte` |
| `numero` | Número ou palavra gigante centralizada com legenda mono | `texto` (aceita HTML), `legenda`, `tamanho`, `topo`, `cor`, `pilulas` |
| `leitura` | Terminal rolando uma árvore de arquivos com contador subindo | `titulo`, `tituloJanela`, `arquivos` (lista de linhas), `rotuloContador`, `valorInicial`, `valorFinal` |
| `grafo` | Nós aparecendo e se conectando (os nós estão definidos no código: adapte antes de usar) | `titulo`, `rotulo`, `layout` |
| `imagem` | Print real (site, repositório) num cartão com moldura | `src`, `x`, `y`, `largura`, `alturaImagem`, `rotulo`, `pilulas`, `centralizarPilulas`, `inicioPilulas`, `fundoCheio` |
| `ilustracao` | PNG transparente (ícone/objeto 3D gerado) flutuando com halo verde | `src`, `x`, `y`, `largura`, `alturaImagem`, `rotulo`, `legenda`, `tamanhoLegenda`, `pilulas`, `fundoCheio`, `layout: "dividido"`, `flutuar`, `brilho`, `atrasoEntrada` |

## Itens do `painel`
- Texto simples: `{"texto": "não revelou as instruções", "inicio": 1.6}` (`inicio` = segundos depois que o motion começou; sincronize com a fala).
- Com cor: `{"texto": "recusa menos?", "cor": "amarelo", "inicio": 7.2}`.
- Cartão: `{"tipo": "cartao", "rotulo": "sem jailbreak", "valor": "direto", "detalhe": "criticou o profissional", "largura": 400, "apagado": true, "inicio": 1.0}`.

## Lados da `comparacao`
`{"rotulo": "sem graphify", "valor": 0.2593, "prefixo": "US$ ", "casasDecimais": 4, "sufixo": "", "unidade": "custo estimado · 367,6 mil tokens", "vencedor": true}`.
Use sempre os números reais da tela e preencha `fonte` com a origem ("números da tela do /cost").

## Layout dividido
Com `"layout": "dividido"`, o `renderizar_parte.py` reduz a tela gravada para 1280x720 em x=592, y=180 e o motion ocupa a coluna da esquerda (~0 a 560 px).
Textos longos nessa coluna estouram por baixo da tela: itens com até ~25 caracteres.

## Exemplos reais
`modelos/roteiro_motions_modelo.json` tem um exemplo de cada tipo, tirado do primeiro vídeo editado.
