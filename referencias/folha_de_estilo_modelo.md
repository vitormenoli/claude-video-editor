# Folha de estilo de edição

Este arquivo é copiado para a sua pasta de edição como `folha_de_estilo.md`. Edite à vontade: o Claude lê essa folha antes de cada vídeo e segue o que estiver aqui.
Os números (duração, volumes, prévias) ficam no `config_editor.json`; aqui ficam as regras de gosto.

## Canal
- Nome do canal, idioma e tom (ex.: direto e informal).
- Tipo de vídeo (ex.: gravação de tela + voz, tutoriais e testes de ferramentas).

## Cortes
- Toda gagueira sai: palavra ou sílaba repetida, falso começo, frase recomeçada. Fica sempre a **última** versão.
- Silêncio longo sai quase inteiro, deixando um respiro curto de cada lado.
- Esperas longas (instalação, programa carregando, IA respondendo) saem.
- Nunca cortar algo que mude o sentido. Na dúvida, manter.
- Se a pessoa disser na gravação algo como "corta essa parte", cortar a parte e o próprio recado.
- Sem zoom nos cortes.

## Abertura e encerramento
- Sem vinheta no começo: o vídeo começa direto na primeira fala.
- Cartão de abertura de 3 a 5 s com o título, entrando enquanto a pessoa já fala.
- Encerramento (se configurado) no final, inteiro, com crossfade.

## Motions
- Quando a tela fica parada enquanto a pessoa explica, entra um motion (painel, número, etiqueta).
- Tela sem importância → motion em tela cheia. Tela importante → tela à direita e motion à esquerda (layout dividido).
- Etiquetas discretas no canto para comandos digitados, nomes de ferramentas, números e avisos.
- Título de capítulo discreto a cada bloco do roteiro, com uma transição curta entre blocos.
- Nunca mais de um elemento ao mesmo tempo e nunca cobrindo o que importa na tela.
- Cor de destaque para palavras-chave; vermelho só para alerta, amarelo só para dúvida.
- Números de testes sempre os reais da tela, com a fonte em letra pequena.
- Logo de outra marca só por print real do site oficial, nunca redesenhado.

## Conteúdo sensível
- Senhas, chaves de API, dados pessoais e qualquer coisa que o roteiro mandar esconder ficam desfocados.

## Áudio
- Voz normalizada (padrão -14 LUFS).
- Música de fundo bem baixa (se configurada), abaixando ainda mais quando a pessoa fala.
- Efeitos sonoros só nos motions, bem baixos.

## Entrega
- Legenda `.srt` para subir no YouTube (não queimada no vídeo).
- Capítulos no formato "0:00 Título".
- Descrição para o YouTube com os links citados no vídeo e os capítulos.
