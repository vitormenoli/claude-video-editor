# Folha de estilo de edição · vídeos longos do canal Vitor Menoli

Pesquisa feita em 29/10/2026 nos 3 longos mais recentes (Jailbreak GPT 6, Jailbreak Universal, Higgsfield grátis), nos Shorts da playlist "Radar de IA ⚡" e no vitormenoli.com. As regras abaixo foram confirmadas pelo Vitor e testadas no vídeo do Graphify.

## Canal
- Vitor Menoli (@vitor.menoli), PT-BR, tom direto, informal e honesto, sem hype vazio. Tema: IA na prática para devs.
- Longos com **no mínimo 8 min** e até ~15 min (não pode ficar longo e cansativo). Gravação de tela + voz.
- Se depois dos cortes o vídeo ficar abaixo de 8 min, **avisar o Vitor antes do render final**. Nunca esticar com fala inventada, silêncio ou espera sem motivo.
- Títulos: "Como Usar XYZ" / "Testei ABC", com 1 ou 2 emojis no fim e sem hashtag.

## Identidade visual (todo elemento gráfico)
- Fundo #0A0A0A com grade técnica sutil e brilho verde; destaque verde #1CFC77; texto #F2F2F2 e cinza #9BA19D.
- Títulos em Space Grotesk 700, caixa alta, brancos com a palavra-chave em verde. Etiquetas e dados em JetBrains Mono. Corpo em Inter.
- Uma cor de destaque. Vermelho só para alerta/resultado negativo, amarelo só para dúvida ("-80%?").
- Marca "› VITOR MENOLI" em mono, cinza. Logo: `midia/Logo VM.png` (usar o arquivo, nunca redesenhar).
- Nada de clichê de IA (cérebro com rede neural, cubo flutuante, skyline).
- Logo de outra marca: só print real do site/repositório oficial, capturado com Playwright (`motions/capturar.js`).

## Imagens geradas (ícones, objetos, tags) junto com os motions
Regra pedida pelo Vitor em 29/10/2026: além dos motions, usar imagens geradas para prender mais a atenção.
- **O que gerar:** ícones e objetos 3D que ilustram a ideia da fala (cadeado, escudo, chave, balão de conversa, terminal, foguete, troféu, alerta) e tags/selos visuais. Sempre no clima do canal: fundo escuro, acento verde #1CFC77, acabamento premium, um objeto só por imagem.
- **Proibido na imagem:** logo ou marca de outra empresa, texto escrito (o texto fica no motion, na nossa fonte), pessoas ou rostos, imitação de site/app real, clichê de IA (cérebro com rede neural, robô humanoide, cubo flutuante, skyline).
- **Quantidade:** mais ou menos 1 a cada 1 ou 2 minutos (6 a 10 por vídeo). Elas não substituem os motions e entram nos momentos em que a tela fica parada.
- **Como entram:** modelo `ilustracao` do motor (PNG transparente flutuando, com halo verde, legenda e pílulas opcionais). Pode ser em tela cheia (`fundoCheio: true`) quando a tela não importa, ou à esquerda no layout dividido (`layout: "dividido"`) quando a tela importa. Para print real use o modelo `imagem` (com moldura).
- Continua valendo: **nunca mais de um elemento por vez** e nunca cobrir algo importante da tela.
- **Onde gerar:** no ChatGPT (chatgpt.com), pela extensão Claude in Chrome no Chrome do Vitor. Passo a passo em `00_LEIA_PRIMEIRO.md`.

## Abertura
- Sem vinheta. O vídeo começa direto na fala do gancho (normalmente sobre o papel de parede do desktop com a logo).
- Cartão de abertura de 3 a 5 s com o título, entrando enquanto ele já fala o gancho. O gancho não pode atrasar.

## Cortes (o principal)
- **Toda e qualquer gagueira sai**: palavra/sílaba repetida, "o o", "aí aí", falso começo, frase recomeçada. Fica sempre a **última** versão.
- **Silêncio a partir de ~0,5 s sai quase inteiro**: ficam só uns centésimos de respiro de cada lado (0,08 s).
- Nunca cortar algo que mude o sentido. Na dúvida, manter.
- Esperas longas (instalação, agente rodando) saem mesmo que a tela "pule".
- Se o Vitor falar algo como "Claude, se estiver editando, corte X", cortar X e o próprio recado.
- Sem zoom nos cortes (o canal não usa jump cut com zoom).

## Enquadramento e motions
- Tela gravada inteira 1920x1080, com a barra de tarefas, sem recorte.
- Quando a tela fica muito tempo parada enquanto ele explica → **entram motions** (com sons de animação bem baixos).
- Tela sem importância (papel de parede, espera) → motion em tela cheia.
- Tela importante → **tela gravada à direita** (1280x720 em x=592, y=180) e motion/imagem na esquerda (`"layout": "dividido"`).
- Etiquetas pequenas (pílulas mono, comandos, nome de ferramenta) discretas, no canto, sem cobrir o que importa. Nunca mais de um elemento ao mesmo tempo.
- Comandos digitados ganham cartão "terminal" com o comando exato da tela. Avisos importantes viram pílula ("atenção: são dois Y no final").
- Números de teste: sempre os reais da tela (no Graphify foi o `/cost`), com a fonte em letra pequena.
- Título de capítulo discreto no canto superior esquerdo ("02 / 08 · O que é") a cada bloco do roteiro.
- Sem legenda queimada (vídeo longo). A legenda vai em `.srt` para subir no YouTube.

## Conteúdo sensível na tela (desfoque)
- Texto que não pode aparecer (ex.: prompt de jailbreak que não é compartilhado) é **desfocado** com `desfoques_fonte` no `roteiro_motions.json`, com uma pílula explicando ("prompt oculto · não compartilhado").
- Palavrões pesados escritos na tela (respostas de IA, prompts) também são desfocados, por segurança com a monetização (o canal entrou no YPP em 20/10/2026). A fala do Vitor e as pílulas contam o resultado.

## Transições
- Entre blocos do roteiro: transição discreta (linha verde fina varrendo + escurecimento rápido, 0,4 s). Nada que chame muita atenção.
- Dentro do bloco: corte seco.
- Do vídeo para o encerramento: **crossfade de 0,5 s** (mesclando as telas, sem corte seco).

## Áudio
- Voz: -14 LUFS, pico máximo -1,5 dBTP, passa-alta 70 Hz, redução leve de ruído e compressão leve.
- **Música de fundo sempre**, bem baixa mas audível (no CapCut ele usa vídeo 300 e música 1): -40 LUFS nas pausas (~26 dB abaixo da voz) e -8 dB de ducking com voz. Fade in de 1 s e fade out de 1,5 s terminando quando o encerramento entra. Loop limpo com crossfade.
- Efeitos sonoros só nos motions, bem baixos (-24 dB): pop, sopro, contador, digitação, impacto (`motions/sons`).

## Encerramento
- `midia/Intro Logo animada.mp4` (6 s, 1920x1080, 30 fps, com áudio próprio) vai **sempre no final**, depois da última fala. Não encurtar, não acelerar e não sobrepor nada além do crossfade de entrada. O áudio dele entra no volume original.
- Sem tela final extra de 15 s.

## Entrega
- MP4 H.264 1920x1080 30 fps, CRF 18, preset veryfast, AAC 192 kbps. Nome: `<nome do bruto>_editado.mp4`, na mesma pasta do bruto.
- Prévias dos primeiros 60 s e dos últimos 30 s antes do render final.
- Arquivos pequenos: `cortes.csv`, `capitulos.txt` (formato "0:00 Título"), `.srt` e um `.zip` com o código.
- Atualizar a seção "Descrição" do `roteiro.md`, mantendo o texto original e acrescentando os links citados no vídeo e os capítulos.
- Nunca sobrescrever o bruto nem o encerramento. Nunca inventar fala nem gerar voz sintética.
