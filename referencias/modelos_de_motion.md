# Modelos de motion (`motions/motor.html`)

Todo motion é um objeto dentro de `"motion"` no `roteiro_motions.json`, com `tipo` e `duracao` (segundos) obrigatórios.
Coordenadas em pixels de um quadro 1920x1080. Em títulos e legendas, `*palavra*` fica na cor de destaque.
Cores especiais nos itens: `"cor": "amarelo"` (dúvida) e `"cor": "vermelho"` (alerta).
A cor de destaque, a cor de fundo e a marca d'água vêm do `config_editor.json` (`motions.cor_destaque`, `motions.cor_fundo`, `motions.marca_dagua`) quando o render usa `--identidade=<pasta>/config_editor.json`.

| Tipo | Como aparece no vídeo | Parâmetros |
|---|---|---|
| `abertura` | Cartão com o título do vídeo, sobre a tela, nos primeiros segundos | `x`, `y`, `largura`, `rotulo`, `linhas` (lista), `tamanhoTitulo`, `pilulas` (lista) |
| `capitulo` | Título de capítulo discreto no canto ("02 / 04 · Download") | `x`, `y`, `numero`, `titulo` |
| `transicao` | Linha fina varrendo a tela + escurecimento rápido (0,4 s) | `intensidade` (0 a 1) |
| `pilula` | Etiqueta pequena (comando, ferramenta, número, aviso) | `x`, `y`, `texto`, `rotulo` (texto pequeno acima), `alinhamento: "direita"` (o `x` vira a borda direita) |
| `comando` | Janela de terminal com o comando sendo digitado | `x`, `y`, `largura`, `comando`, `tituloJanela`, `prompt`, `tamanhoFonte`, `duracaoDigitacao`, `destaqueFinal`, `aviso`, `avisoAcima` |
| `painel` | Título + itens que entram um a um; tela cheia ou à esquerda da tela gravada | `linhas`, `rotulo`, `itens`, `layout: "dividido"`, `topo`, `tamanhoTitulo`, `itensEmColuna`, `semFundoAnimado` |
| `comparacao` | Dois números lado a lado com barras e contagem (resultado de teste) | `titulo`, `subtitulo`, `lados` (2 objetos), `delta`, `deltaNegativo`, `fonte` |
| `numero` | Número ou palavra gigante centralizada com legenda mono | `texto` (aceita HTML), `legenda`, `tamanho`, `topo`, `cor`, `pilulas` |
| `leitura` | Terminal rolando uma árvore de arquivos com contador subindo | `titulo`, `tituloJanela`, `arquivos` (lista de linhas), `rotuloContador`, `valorInicial`, `valorFinal` |
| `imagem` | Imagem (print real de site, foto, PNG) num cartão | `src`, `x`, `y`, `largura`, `alturaImagem`, `rotulo`, `pilulas`, `centralizarPilulas`, `inicioPilulas`, `fundoCheio` |

## Itens do `painel`
- Texto simples: `{"texto": "instalou sem erro", "inicio": 1.6}` (`inicio` = segundos depois que o motion começou; sincronize com a fala).
- Com cor: `{"texto": "funciona offline?", "cor": "amarelo", "inicio": 6.0}`.
- Cartão: `{"tipo": "cartao", "rotulo": "antes", "valor": "42 s", "detalhe": "programa A", "largura": 400, "apagado": true, "inicio": 1.0}`.

## Lados da `comparacao`
`{"rotulo": "FFmpeg", "valor": 13.8, "prefixo": "", "casasDecimais": 1, "sufixo": " s", "unidade": "tempo total", "vencedor": true}`.
Use sempre os números reais da tela e preencha `fonte` com a origem ("números da tela · cronômetro do terminal").

## Imagens
- `src` pode ser um caminho absoluto do computador (`C:/.../_edicao/imagens/site.png`): o `renderizar.js` converte para `file://`.
- Print de site ou repositório: `node motions/capturar.js <url> <saida.png> [seletor_css]`.

## Layout dividido
Com `"layout": "dividido"`, o `renderizar_parte.py` reduz a tela gravada para 1280x720 em x=592, y=180 e o motion ocupa a coluna da esquerda (~0 a 560 px).
Textos longos nessa coluna estouram por baixo da tela: itens com até ~25 caracteres.

## Exemplo
`modelos/roteiro_motions_modelo.json` tem um exemplo de cada tipo.
