# Imagens geradas no ChatGPT (ícones, objetos 3D, tags)

Além dos motions, o vídeo usa de 6 a 10 imagens geradas (mais ou menos 1 a cada 1 ou 2 minutos) para prender a atenção nos momentos de tela parada.
Quem gera é o próprio Claude, pelo ChatGPT, usando a extensão **Claude in Chrome** no Chrome do usuário, que já está logado no ChatGPT.

## O que pode e o que não pode
- **Pode:** um objeto por imagem que ilustra a fala (cadeado, escudo, chave, balão de conversa, terminal, foguete, troféu, alerta), tags e selos visuais, no clima do canal.
- **Não pode:** logo ou marca de outra empresa (para isso, só print real com `motions/capturar.js`), texto dentro da imagem (o texto fica no motion, na fonte do canal), pessoas ou rostos, imitação de site ou app real, clichê de IA (cérebro com rede neural, robô humanoide, cubo flutuante, skyline).

## Passo a passo
1. Carregue as ferramentas do navegador (`mcp__claude-in-chrome__*`) de uma vez e comece com `tabs_context_mcp`. Abra uma aba nova.
2. Abra `https://chatgpt.com`. Se pedir login, senha, captcha, assinatura, pagamento ou aceite de termos: **pare e avise o usuário**. O Claude não digita senha nem aceita nada.
3. Num chat novo, peça **todas as imagens numa mensagem só**, numeradas:
   > Gere N imagens separadas, todas no mesmo estilo, para usar como elementos gráficos em um vídeo do YouTube:
   > 1. um cadeado aberto
   > 2. um escudo de proteção
   > 3. …
   > Estilo de todas: ícone 3D realista e premium, um único objeto centralizado, materiais escuros (grafite, vidro fosco, metal escovado) com brilho e reflexos verde neon #1CFC77, iluminação de estúdio, sombra suave. PNG com fundo transparente, formato quadrado. Sem texto, sem letras, sem números, sem logos ou marcas, sem pessoas.
4. Espere todas ficarem prontas e baixe cada uma pelo botão de download da imagem (o usuário precisa ter autorizado esses downloads). O Chrome salva na pasta Downloads.
5. Copie para `_edicao/imagens/` com nomes descritivos (`cadeado_aberto.png`) e leve para `motions/imagens/` da máquina que renderiza os motions.
6. Confira a transparência: `python3 -c "from PIL import Image; im = Image.open('cadeado_aberto.png'); print(im.mode, im.getextrema()[-1])"` precisa dar `RGBA` com mínimo 0. Se vier com fundo, peça no mesmo chat: "refaça a imagem 2 com fundo transparente".
7. Use com o modelo `ilustracao`:
```json
{"frase": "será que a gente vai conseguir deixar essa ia sem censura", "ajuste": -0.2,
 "motion": {"tipo": "ilustracao", "duracao": 5.0, "fundoCheio": true, "src": "imagens/cadeado_aberto.png",
            "x": 760, "y": 200, "largura": 400, "rotulo": "a pergunta", "legenda": "Sem *censura*?", "pilulas": ["mais direto", "recusa menos?"]}}
```
   No layout dividido (tela importante à direita): `"layout": "dividido"`, `"x": 110`, `"largura": 360`.
8. Antes do render, confira na folha de contato: nada de texto, logo ou pessoa na imagem, e nada importante da tela coberto.
