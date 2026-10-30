---
name: claude-video-editor
description: Edita vídeos longos do YouTube (gravação de tela + voz) por código, do bruto ao MP4 final - cortes de silêncio e gagueira com Whisper, motions animados, música com ducking, legenda .srt, capítulos e descrição. Use quando pedirem para editar um vídeo bruto ou configurar a pasta de edição.
---

# Claude Video Editor

Esta skill transforma um vídeo bruto (gravação de tela + voz) num vídeo pronto para o YouTube, sem editor de vídeo:
- corta **todo** silêncio, gagueira, falso começo e frase recomeçada (fica sempre a última versão);
- corta as esperas (instalação, programa carregando, IA respondendo);
- coloca **motions** animados (título, capítulos, painéis, etiquetas, números, comparações) quando a tela fica parada;
- desfoca o que não pode aparecer;
- mixa a voz com música de fundo baixinha e ducking, e fecha com o encerramento do canal (os dois são opcionais);
- entrega o vídeo, a legenda `.srt`, os capítulos e a descrição para o YouTube.

Ferramentas: Python, FFmpeg, faster-whisper e Playwright. Quem edita é o Claude; a pessoa só coloca os arquivos na pasta e aprova.

Neste guia, `<SKILL>` é a pasta onde está este arquivo e `<PASTA>` é a pasta de edição escolhida pela pessoa.

## Regras que nunca mudam
1. **Nunca invente fala.** Edição é cortar e decorar o que foi gravado. Nada de frase nova, voz sintética ou texto atribuído à pessoa.
2. **Nunca altere nem apague os arquivos da pessoa** (bruto, partes, roteiro, música, encerramento). Tudo de trabalho fica em `<PASTA>/_edicao`.
3. **Números de teste são sempre os reais da tela**, com a fonte em letra pequena.
4. **Logo de outra marca só por print real** do site oficial (`motions/capturar.js`). Nunca redesenhar.
5. **Na dúvida, não corte.** Nenhum corte pode mudar o sentido da fala.
6. Siga a `folha_de_estilo.md` e o `config_editor.json` da pasta de edição: eles mandam mais que os padrões deste guia.

---

## 1. Primeira vez: configurar a pasta de edição
Faça isto quando a pessoa instalar a skill, pedir para configurar, ou quando `<PASTA>/config_editor.json` não existir.

### 1.1 Pedir a pasta
- Peça a pasta que vai ser usada para editar os vídeos (ex.: `C:\Users\nome\Videos\Edicoes`).
- No Claude Code, peça o caminho (ou use a pasta aberta, se a pessoa disser que é ela). No app do Claude com o computador conectado, peça acesso à pasta.

### 1.2 Instalar tudo
```bash
python <SKILL>/scripts/instalar.py --baixar-modelo=large-v3
```
- Ele instala sozinho os pacotes Python, o Playwright e o Chromium do Playwright, e baixa o modelo do Whisper (o `large-v3` tem ~3 GB).
- Python 3.10+, FFmpeg (com libx264 e libvpx-vp9) e Node.js 18+ são programas do sistema. Se faltar algum, o script diz exatamente o que falta e o comando para instalar (winget no Windows, brew no macOS, apt no Linux). **Mostre isso à pessoa** e pergunte se pode rodar o comando; depois rode o `instalar.py` de novo até sair "Tudo pronto para editar".
- No Windows o comando pode ser `python` ou `py`; no macOS/Linux, `python3`.

### 1.3 Perguntar as configurações
Pergunte numa mensagem só (ou com perguntas de múltipla escolha), já com os padrões:

| # | Pergunta | Padrão | Campo no `config_editor.json` |
|---|---|---|---|
| 1 | Duração mínima e máxima do vídeo final | 8 e 15 min | `duracao_minima_min`, `duracao_maxima_min` |
| 2 | Quer prévias para aprovar antes do vídeo final? Ou o resultado final direto? | prévias de 60 s (início) e 30 s (fim) | `previas`, `previa_inicio_s`, `previa_fim_s` |
| 3 | Vai usar música de fundo? | sim, `Midia do Canal/musica_fundo.mp3` | `musica_de_fundo` (`null` = sem música) |
| 4 | Tem um encerramento (vinheta/logo animada) para o final? | sim, `Midia do Canal/encerramento.mp4` | `encerramento` (`null` = sem) |
| 5 | Identidade dos motions: marca d'água, cor de destaque e cor de fundo | sem marca, `#4F8CFF`, `#0F1115` | `motions.marca_dagua`, `motions.cor_destaque`, `motions.cor_fundo` |
| 6 | Efeitos sonoros baixinhos nos motions? | sim | `efeitos_sonoros` |
| 7 | Qualidade da transcrição | `large-v3` (melhor); `medium` ou `small` (mais rápidos, erram mais) | `modelo_whisper` |
| 8 | Volume da voz | -14 LUFS (padrão do YouTube) | `voz_alvo_lufs` |
| 9 | Entregar legenda `.srt`, capítulos e descrição? | sim | `legenda_srt`, `capitulos`, `descricao_youtube` |

### 1.4 Criar a pasta
```bash
python <SKILL>/scripts/configurar_pasta.py "<PASTA>" --config='{"duracao_minima_min": 8, "previas": true, "musica_de_fundo": null, "motions": {"marca_dagua": "› MEU CANAL"}}'
```
Cria:
```
<PASTA>/
  Arquivos Brutos/     vídeo bruto + roteiro (com LEIA-ME.txt explicando)
  Midia do Canal/      musica_fundo.mp3, encerramento.mp4, logo.png (opcionais)
  Resultado Final/     onde sai o vídeo editado
  _edicao/             arquivos de trabalho
  config_editor.json   as respostas acima
  folha_de_estilo.md   regras de edição (a pessoa pode editar)
```
Rodar de novo não apaga nada; serve também para mudar uma configuração depois.

### 1.5 Explicar o uso
Diga à pessoa, em poucas linhas:
- coloque em **Arquivos Brutos** o vídeo bruto: **um vídeo só**, ou várias partes com os nomes **"Parte 1.mp4", "Parte 2.mp4"...** (juntadas nessa ordem);
- coloque junto o **roteiro** em `.md` ou `.txt`: título, descrição, blocos/assuntos na ordem, links citados e o que não pode aparecer na tela;
- coloque a música e o encerramento em **Midia do Canal**, se escolheu usar;
- depois é só pedir: "edita o vídeo".

---

## 2. Editar um vídeo

### Etapa 0 · Preparar
```bash
python <SKILL>/scripts/preparar_video.py "<PASTA>"
```
- Confere a pasta **Arquivos Brutos**: um vídeo só, ou partes "Parte N" (junta na ordem). Se tiver vídeos fora do padrão, ele para e explica; passe a explicação para a pessoa.
- Acha o roteiro (`.md`/`.txt`), extrai os áudios, mede a música, confere o encerramento e gera `_edicao/configuracao_video.json` e `_edicao/decisoes.json`.
- Leia a `folha_de_estilo.md`, o `config_editor.json` e o roteiro inteiro antes de seguir.
- Se faltar algo que o roteiro e a folha de estilo não respondem, pergunte numa mensagem só.

### Etapa 1 · Transcrição e cortes
Dentro de `<PASTA>/_edicao`:
```bash
python <SKILL>/scripts/transcrever_blocos.py large-v3 voz_16k.flac transcricao_large.jsonl blocos.txt
python <SKILL>/scripts/transcrever_disfluencias.py large-v3 voz_16k.flac silencios_03.txt transcricao_disfluencias.jsonl
```
(use o `modelo_whisper` do config). As duas demoram; rode em segundo plano e acompanhe.

- Leia **as duas** transcrições inteiras. A limpa esconde as retomadas; a de disfluências mostra cada tomada repetida.
- Anote em `decisoes.json` (exemplo em `<SKILL>/modelos/decisoes_modelo.json`):
  - `remover`: retomadas, frases abandonadas, trechos que a pessoa mandou cortar durante a gravação ("corta essa parte": corte a parte e o recado). Fica sempre a **última** versão.
  - `manter`: trechos que nenhum corte automático pode tocar.
  - `correcoes_texto`: nomes que o Whisper erra, para a legenda.
  - `"exato": true` quando o ponto do corte precisa ser exatamente aquele.
- Os tempos do Whisper marcam as palavras ~0,3 s **antes** do som real e erram mais perto de hesitação. Para cortes manuais, olhe a energia da voz: `python <SKILL>/scripts/ferramentas/rajadas.py voz_16k.flac transcricao_disfluencias.jsonl 90:92` e corte no buraco entre as rajadas.

```bash
python <SKILL>/scripts/montar_cortes.py transcricao_large.jsonl silencios_03.txt decisoes.json . transcricao_disfluencias.jsonl voz_16k.flac
```
Sozinho ele corta: silêncio acima de `silencio_minimo_s` (deixando `respiro_s` de cada lado), palavra repetida em sequência (menos ênfase, como "muito muito"), esperas longas sem fala (só a partir de uma pausa real, e nunca onde há voz); e encaixa cada corte no respiro mais próximo.

**Conferência obrigatória:**
```bash
python <SKILL>/scripts/montar_voz_editada_16k.py voz_16k.flac mapa_tempo.json voz_editada_16k.wav
python <SKILL>/scripts/transcrever_voz_editada.py large-v3 voz_editada_16k.wav transcricao_voz_editada "nomes próprios do vídeo"
```
- Leia o `transcricao_voz_editada.txt` inteiro: é exatamente o que vai ao ar. Sobrou gagueira ou foi comida alguma palavra? Ajuste o `decisoes.json` e repita.
- Compare a duração final com `duracao_minima_min` e `duracao_maxima_min`. Fora do intervalo: avise a pessoa antes de seguir (nunca estique com silêncio ou fala inventada; se passar do máximo, sugira o que pode sair).
- Fechamento da etapa para a pessoa: duração antes/depois, número de cortes, retomadas que saíram.

### Etapa 2 · Motions
1. Escreva `_edicao/roteiro_motions.json` (exemplo em `<SKILL>/modelos/roteiro_motions_modelo.json`, referência em `<SKILL>/referencias/modelos_de_motion.md`). Cada motion é ancorado numa **frase do bruto** (como na `transcricao_large.jsonl`, sem pontuação) com `depois_de` e `ajuste`. Os caminhos e volumes já vêm do `configuracao_video.json`.
2. Onde colocar o quê:
   - `abertura` de 3 a 5 s com o título, entrando enquanto a pessoa já fala;
   - `transicao` + `capitulo` no início de cada bloco do roteiro (com `"capitulo": "Título"` no item, viram os capítulos do YouTube);
   - tela parada enquanto a pessoa explica → `painel`, `numero` ou `comparacao`;
   - tela sem importância → motion em tela cheia; tela importante → `"layout": "dividido"` (tela à direita, motion à esquerda);
   - comandos digitados, ferramentas, números e avisos → `pilula` ou `comando`, discretos no canto;
   - **nunca mais de um elemento ao mesmo tempo** (o `planejar.py` avisa sobreposição) e nunca cobrindo o que importa.
3. **Desfoque:** o que não pode aparecer entra em `desfoques_fonte` (tempos do bruto + região em pixels). Ache o intervalo com um mosaico: `ffmpeg -ss <ini> -t <dur> -i <bruto> -vf "fps=2,scale=320:180,tile=6x2" -frames:v 1 mosaico.jpg`.
4. Rode e confira:
```bash
python <SKILL>/scripts/planejar.py transcricao_large.jsonl mapa_tempo.json roteiro_motions.json .
node <SKILL>/motions/renderizar.js especificacoes_motions.json previa --previa --identidade="<PASTA>/config_editor.json"
python <SKILL>/scripts/montar_folha_contato.py plano.json mapa_tempo.json "<bruto>" previa folha
```
   Olhe as folhas de contato (`folha_0.jpg`...): texto estourando (no layout dividido, itens com até ~25 caracteres), etiqueta cobrindo algo importante, sobreposição. Corrija e renderize:
```bash
node <SKILL>/motions/renderizar.js especificacoes_motions.json motions --identidade="<PASTA>/config_editor.json"
```
   (os `.webm` precisam ficar em `_edicao/motions/`; `--so=nome1,nome2` renderiza só alguns).
   Sem `"nome"` fixo, o nome do arquivo vem da posição no roteiro; inserir um motion no meio renomeia os seguintes.

### Etapa 3 · Prévias (se `previas` for `true`)
```bash
python <SKILL>/scripts/montar_video_final.py "<PASTA>" --previas
```
Monta o áudio, renderiza só as partes do começo e do fim e salva em `Resultado Final/Previas/`. Peça para a pessoa aprovar estilo, ritmo e volume da música. Ajuste o que ela pedir e só depois siga.
Com `previas: false`, vá direto para a etapa 4.

### Etapa 4 · Vídeo final
```bash
python <SKILL>/scripts/montar_video_final.py "<PASTA>" --final
python <SKILL>/scripts/montar_srt_editado.py transcricao_voz_editada.jsonl decisoes.json "<PASTA>/Resultado Final/<nome>_editado.srt" <duração do vídeo>
```
- Monta o áudio (voz no alvo de LUFS, música com ducking, efeitos, encerramento), renderiza as partes (reaproveita as que não mudaram), junta tudo em `Resultado Final/<nome>_editado.mp4`, copia `capitulos.txt` e `cortes.csv` e mostra a conferência (resolução, fps, LUFS, duração).
- Confira tela parada demais: `ffmpeg -ss 0 -t 140 -i <video> -an -vf "scale=480:270,freezedetect=n=0.003:d=8" -f null - 2>&1 | grep freeze_` (em pedaços de 140 s). Trechos de mais de ~12 s sem nenhum elemento → mais motion e rode o `--final` de novo (só as partes que mudaram são refeitas).
- Se `descricao_youtube` for `true`, escreva `Resultado Final/descricao_youtube.md`: a descrição do roteiro (sem mudar o texto), os links citados no vídeo e os capítulos com as minutagens finais (o primeiro sempre em 0:00).
- Fechamento para a pessoa: o que ficou pronto, onde está e o que falta. Sem relatório longo. A pasta `_edicao` pode ser apagada depois que o vídeo for publicado.

---

## Padrões (quando o config não disser outra coisa)
- Saída: H.264 1920x1080 30 fps, CRF 18, AAC 192 kbps.
- Voz -14 LUFS, pico -1,5 dBTP, passa-alta 70 Hz, redução leve de ruído e compressão leve.
- Música -40 LUFS nas pausas e -8 dB de ducking com voz, fade in de 1 s e fade out de 1,5 s terminando na entrada do encerramento.
- Efeitos sonoros só nos motions, a -24 dB.
- Transição curta entre blocos (0,4 s), corte seco dentro do bloco, crossfade de 0,5 s para o encerramento; sem encerramento, o vídeo termina com fade de 0,8 s.
- Sem zoom nos cortes e sem legenda queimada.

## Computador remoto (opcional)
Se o vídeo fica no computador da pessoa e o Claude trabalha num ambiente na nuvem ligado a ele, com limite de tempo por comando, veja `referencias/ambiente_remoto.md`: transcrição e motions na nuvem; áudio (uma etapa por comando) e partes (`renderizar_parte.py plano.json N`, uma por comando) no computador; junção com `juntar_final.py`.

## Problemas conhecidos
| Sintoma | Causa | Correção |
|---|---|---|
| Processo da transcrição morre sem erro | Whisper large-v3 + Chromium ao mesmo tempo (falta de RAM) | Um de cada vez |
| Gagueira continua no vídeo | O Whisper "limpa" repetições na transcrição normal | Passada de disfluências + conferência da voz editada |
| Fim de palavra comido | Corte começando no fim marcado pelo Whisper | `montar_cortes.py` só começa espera em pausa real |
| Frase inteira sumiu | A transcrição pulou a frase e ela virou "espera" | Lacuna com voz em mais de 30% do tempo não é cortada |
| Áudio escorrega no fim | Parte com um quadro a menos | Contagem exata de quadros por parte (já feita) |
| Legenda com palavras de tomadas cortadas | Legenda feita da transcrição do bruto | `.srt` feito da transcrição da voz editada |
| "Nenhum vídeo" ou "fora do padrão Parte N" | Arquivos Brutos com nomes misturados | Um vídeo só ou "Parte 1.mp4", "Parte 2.mp4"... |
| FFmpeg sem libvpx-vp9 | Build mínima do FFmpeg | Instalar uma build completa (o `instalar.py` mostra o comando) |
