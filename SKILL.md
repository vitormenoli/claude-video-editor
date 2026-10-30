---
name: editor-video-longo
description: Edita vídeos longos do YouTube (gravação de tela + voz) por código, do bruto ao MP4 final - cortes de silêncio e gagueira com Whisper, motions animados, imagens geradas, música com ducking, legenda .srt e capítulos.
---

# Editor de vídeo longo por código

Esta skill transforma um vídeo bruto (gravação de tela + voz, em português) num vídeo pronto para o YouTube, sem editor de vídeo:
- corta **todo** silêncio, gagueira, falso começo e frase recomeçada (fica sempre a última versão);
- coloca **motions** animados na identidade visual do canal quando a tela fica parada;
- coloca **imagens geradas** (ícones e objetos 3D) para prender a atenção;
- desfoca o que não pode aparecer (prompt secreto, palavrão escrito na tela);
- mixa a voz a -14 LUFS com música de fundo bem baixa e ducking;
- fecha com o encerramento fixo do canal em crossfade;
- entrega o `.srt`, os capítulos e a descrição atualizada.

Tudo é feito com Python, FFmpeg, faster-whisper e Playwright. Quem edita é o Claude; o humano só aprova as prévias.

## Quando usar
- O usuário pede para editar um vídeo longo (tutorial, teste de ferramenta, review) a partir de um bruto e de um roteiro.
- O usuário quer refazer só uma parte do processo: cortes, motions, áudio, legenda ou capítulos.

## Regras que nunca mudam
1. **Nunca invente fala.** Edição é cortar e decorar o que foi gravado. Nada de frase nova, voz sintética ou texto atribuído à pessoa.
2. **Nunca sobrescreva o bruto nem o encerramento.** Trabalhe numa pasta `_edicao` ao lado do bruto.
3. **Números de teste são sempre os reais da tela**, com a fonte em letra pequena. Nunca arredonde a favor da tese.
4. **Logo de outra marca só por print real** do site ou repositório oficial (`motions/capturar.js`). Nunca redesenhar nem gerar.
5. **Na dúvida, não corte.** Nenhum corte pode mudar o sentido da fala.
6. **Avise antes de apagar ou substituir** qualquer arquivo do usuário.
7. **Aprovação antes do final:** prévias dos primeiros 60 s e dos últimos 30 s vão para a pessoa aprovar antes do render final.

## Requisitos
- Python 3.10+ com `pip install -r requirements.txt` (faster-whisper, numpy, Pillow).
- FFmpeg 4.4+ com `libx264` e `libvpx-vp9` (`ffmpeg -codecs | grep vp9`).
- Node 18+ com `npm install` e `npx playwright install chromium` (para os motions).
- ~8 GB de RAM livre para o modelo `large-v3`. **Não rode o Whisper large-v3 e o Playwright ao mesmo tempo**: falta memória e o processo morre.
- Arquivos do canal em `midia/` (ver `midia/LEIA.md`): música de fundo, encerramento e logo.

## Estrutura
```
SKILL.md                     este guia
scripts/                     pipeline (todos em Python, com docstring de uso no topo)
  dividir_em_blocos.py         limites dos blocos de transcrição (~8 min, em silêncios)
  transcrever_blocos.py        1ª passada: transcrição limpa, tempo por palavra
  transcrever_disfluencias.py  2ª passada: prompt cheio de hesitações, pega gagueira e falso começo
  montar_cortes.py             cortes.csv, mapa_tempo.json, transcricao_editada.txt
  montar_voz_editada_16k.py    voz já editada, para conferência
  transcrever_voz_editada.py   transcrição de conferência (o que o espectador vai ouvir)
  planejar.py                  roteiro_motions.json -> plano.json, especificacoes_motions.json, capitulos.txt
  montar_folha_contato.py      motions compostos sobre quadros reais do bruto, para conferir
  montar_audio.py              voz + música + efeitos + encerramento, em etapas
  renderizar_parte.py          renderiza uma parte de 40 s do vídeo (cortes, motions, desfoques)
  juntar_final.py              junta as partes + encerramento com crossfade; também gera as prévias
  montar_srt_editado.py        legenda final a partir da transcrição da voz editada
  ferramentas/rajadas.py       energia da voz x palavras do Whisper, para cortes manuais exatos
motions/
  motor.html                   todos os modelos de motion (HTML + CSS + JS, identidade visual nas variáveis CSS)
  renderizar.js                Playwright -> WebM VP9 com transparência, 1920x1080, 30 fps
  capturar.js                  print real de site/repositório oficial
  sons.py, sons/               efeitos sonoros originais (pop, sopro, contador, digitação, impacto)
  fontes/                      Inter, JetBrains Mono, Space Grotesk (OFL)
  imagens/                     prints e imagens geradas usados pelos motions
modelos/                     decisoes_modelo.json e roteiro_motions_modelo.json (exemplos reais)
referencias/                 folha de estilo de exemplo, modelos de motion, imagens geradas, ambiente remoto
midia/                       música, encerramento e logo do canal (não versionados)
```

## Antes de começar
1. Leia a folha de estilo do canal (`referencias/folha_de_estilo_exemplo.md` é a do canal Vitor Menoli; troque pela do seu canal). Ela manda em tudo: duração, cores, quando entra motion, volume da música.
2. Leia o roteiro do vídeo inteiro: título, blocos (viram capítulos), o que não pode aparecer na tela, links citados.
3. Crie a pasta `_edicao` ao lado do bruto e copie para ela `scripts/`, `motions/` e os modelos.
4. Pergunte só o que a folha de estilo e o roteiro não respondem, numa mensagem só.

## Etapa 1 · Transcrição e cortes
```bash
ffmpeg -i bruto.mp4 -vn -ac 1 -ar 16000 -c:a flac voz_16k.flac
ffmpeg -i bruto.mp4 -vn -ac 1 -ar 48000 -c:a pcm_s16le voz_48k.wav
ffmpeg -i voz_16k.flac -af silencedetect=noise=-40dB:d=0.3 -f null - 2> silencios_03.txt
python3 dividir_em_blocos.py silencios_03.txt <duracao_do_bruto> blocos.txt
python3 transcrever_blocos.py large-v3 voz_16k.flac transcricao_large.jsonl blocos.txt
python3 transcrever_disfluencias.py large-v3 voz_16k.flac silencios_03.txt transcricao_disfluencias.jsonl
```
- As duas transcrições demoram (o large-v3 em CPU leva uns 10 a 15 min para 20 min de áudio). Rode em segundo plano e acompanhe o log.
- Leia **as duas** inteiras. A limpa esconde as retomadas; a de disfluências mostra cada tomada ("Eu vou testar o Claude antes e depois... / Eu vou testar o Claude antes e depois de... / Eu vou testar...").
- Anote em `decisoes.json` (modelo em `modelos/`):
  - `remover`: retomadas, frases abandonadas, trechos que a pessoa pediu para cortar durante a gravação ("Claude, se estiver editando, corte essa parte" — corte a parte e o recado). Fica sempre a **última** versão.
  - `manter`: trechos que nenhum corte automático pode tocar.
  - `correcoes_texto`: nomes que o Whisper erra ("Cloud" → "Claude"), aplicados só na legenda e no cortes.csv.
  - `"exato": true` quando o ponto do corte precisa ser exatamente aquele.
- **Tempos do Whisper** marcam as palavras ~0,3 s **antes** do som real e erram até ~1 s perto de hesitação. Para cortes manuais, use `ferramentas/rajadas.py voz_16k.flac transcricao_disfluencias.jsonl 90:92` e corte no buraco entre as rajadas de energia.

```bash
python3 montar_cortes.py transcricao_large.jsonl silencios_03.txt decisoes.json . transcricao_disfluencias.jsonl voz_16k.flac
```
O que ele faz sozinho:
- silêncio a partir de ~0,45 s (pela energia RMS em janelas de 10 ms, limiar -40 dB) sai, deixando 0,08 s de respiro de cada lado;
- palavra ou sílaba repetida em sequência sai (fica a última), exceto ênfase ("muito muito") e repetição em fim de frase;
- esperas longas sem fala (instalação, IA respondendo) saem, mas só começando numa pausa real e nunca numa "lacuna" que tem voz em mais de 30% do tempo;
- todo corte que não é de silêncio é encaixado no respiro mais próximo.

**Conferência obrigatória:**
```bash
python3 montar_voz_editada_16k.py voz_16k.flac mapa_tempo.json voz_editada_16k.wav
python3 transcrever_voz_editada.py large-v3 voz_editada_16k.wav transcricao_voz_editada "nomes próprios do vídeo"
```
Leia o `transcricao_voz_editada.txt` inteiro: é exatamente o que o espectador vai ouvir. Sobrou gagueira ou alguma palavra foi comida? Ajuste o `decisoes.json` e repita.
Confira a duração final contra o mínimo da folha de estilo (no canal de exemplo: **8 min**). Se ficar abaixo, avise antes de seguir; nunca estique com silêncio ou fala inventada.

Fechamento da etapa: duração antes/depois, número de cortes, retomadas que saíram e as perguntas que sobraram.

## Etapa 2 · Motions e imagens
1. Monte o `roteiro_motions.json` (modelo em `modelos/`). Cada motion é ancorado numa **frase do bruto** (como está na `transcricao_large.jsonl`, sem pontuação), com `depois_de` (segundos do bruto, para achar a ocorrência certa) e `ajuste` (adiantar/atrasar). Referência de todos os modelos em `referencias/modelos_de_motion.md`.
2. O bloco `configuracao` leva os caminhos **da máquina onde o vídeo vai ser renderizado** (bruto, voz_48k, música, encerramento) e os volumes.
3. Onde colocar o quê:
   - abertura de 3 a 5 s com o título, entrando enquanto a pessoa já fala o gancho (sem vinheta no começo);
   - `transicao` + `capitulo` no início de cada bloco do roteiro (viram os capítulos do YouTube);
   - tela parada enquanto a pessoa explica → `painel`, `numero` ou `ilustracao`;
   - tela sem importância (papel de parede, espera) → motion em tela cheia;
   - tela importante (resposta da IA, código) → `"layout": "dividido"`: a tela vai para a direita e o motion para a esquerda;
   - comandos digitados, nomes de ferramentas, números e avisos → `pilula` ou `comando`, discretos no canto;
   - **nunca mais de um elemento ao mesmo tempo** (o `planejar.py` avisa sobreposição) e nunca cobrindo o que importa na tela.
4. **Imagens geradas:** de 6 a 10 por vídeo, nos momentos de tela parada, com o modelo `ilustracao`. Como gerar no ChatGPT pela extensão do Chrome: `referencias/imagens_geradas.md`.
5. **Desfoque:** o que não pode aparecer entra em `desfoques_fonte` (tempos do bruto + região em pixels). Ache o intervalo com um mosaico de quadros: `ffmpeg -ss <ini> -t <dur> -i bruto.mp4 -vf "fps=2,scale=320:180,tile=6x2" -frames:v 1 mosaico.jpg`.
6. Rode:
```bash
python3 planejar.py transcricao_large.jsonl mapa_tempo.json roteiro_motions.json .
node motions/renderizar.js especificacoes_motions.json previa --previa
python3 montar_folha_contato.py plano.json mapa_tempo.json bruto.mp4 previa folha
```
7. Olhe as folhas de contato: texto estourando (no layout dividido, itens com até ~25 caracteres), etiqueta cobrindo o prompt digitado ou um aviso da tela, sobreposição. Corrija e renderize de verdade:
```bash
node motions/renderizar.js especificacoes_motions.json saida_webm            # todos
node motions/renderizar.js especificacoes_motions.json saida_webm --so=m013_painel,m020_pilula   # só alguns
```
Os `.webm` vão para `_edicao/motions/`.
- Sem `"nome"` fixo, o nome do arquivo vem da posição no roteiro (`m012_pilula`). Inserir um motion no meio renomeia os seguintes: reaproveite os `.webm` comparando as especificações, ou fixe `"nome"`.

## Etapa 3 · Áudio, partes e prévias
```bash
python3 montar_audio.py plano.json cortar      # corta a voz 48 kHz nos trechos mantidos (micro-fades de 4 ms)
python3 montar_audio.py plano.json medir       # 1ª passada do loudnorm
python3 montar_audio.py plano.json tratar      # passa-alta, redução leve de ruído, compressão leve, -14 LUFS, pico -1,5 dBTP
python3 montar_audio.py plano.json mixar       # música em loop com ducking, efeitos dos motions a -24 dB, encerramento no fim
python3 montar_audio.py plano.json codificar   # AAC 192 kbps
python3 renderizar_parte.py plano.json 0       # repita para cada parte (N = 0 .. partes-1)
python3 juntar_final.py plano.json ../previa_inicio_60s.mp4 --ate=60
python3 juntar_final.py plano.json ../previa_fim_30s.mp4 --ultimos=30
```
- A voz é normalizada em mono e copiada nos dois canais com -3 dB (senão o estéreo fica 3 dB mais alto).
- Cada parte tem o número exato de quadros (fps por pedaço + tpad + trim por quadro); senão o áudio escorrega um quadro por parte.
- Mande as prévias para aprovação (estilo, ritmo, volume da música). Pode renderizar as outras partes enquanto isso, mas **só junte o final depois do ok**.

## Etapa 4 · Render final e entrega
```bash
python3 juntar_final.py plano.json "../<nome do bruto>_editado.mp4"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames,duration -of compact "../<nome>_editado.mp4"
ffmpeg -nostats -i "../<nome>_editado.mp4" -vn -af ebur128=peak=true -f null - 2>&1 | grep -E "I:|Peak:"
ffmpeg -nostats -ss 0 -t 140 -i "../<nome>_editado.mp4" -an -vf "scale=480:270,freezedetect=n=0.003:d=8" -f null - 2>&1 | grep freeze_
python3 montar_srt_editado.py transcricao_voz_editada.jsonl decisoes.json "../<nome>_editado.srt" <duração do vídeo>
```
- Confira: 1920x1080, 30 fps, quadros e duração batendo, -14 LUFS integrado.
- `freezedetect` (em pedaços de 140 s): trechos parados de mais de ~12 s sem nenhum elemento → mais motion ou imagem, e renderize só as partes afetadas.
- Entregue ao lado do bruto: `<nome>_editado.mp4`, `cortes.csv`, `capitulos.txt` ("0:00 Título", o primeiro sempre em 0:00), `<nome>_editado.srt` (para subir no YouTube, não queimar no vídeo) e um zip do código usado.
- Atualize a seção "Descrição" do roteiro: texto original + links citados no vídeo + capítulos com as minutagens finais.
- Fechamento: o que ficou pronto, onde está e o que falta. Sem relatório longo.

## Padrões do canal de exemplo (troque pelos seus)
- Visual: fundo #0A0A0A com grade sutil, verde #1CFC77, texto #F2F2F2, Space Grotesk (títulos), Inter (corpo), JetBrains Mono (etiquetas). As cores ficam nas variáveis CSS do `motor.html`; a marca d'água na constante `MARCA_DAGUA`.
- Vermelho só para alerta, amarelo só para dúvida.
- Transição discreta entre blocos (0,4 s), corte seco dentro do bloco, crossfade de 0,5 s para o encerramento.
- Música -40 LUFS nas pausas, -8 dB de ducking com voz, fade in 1 s, fade out 1,5 s terminando na entrada do encerramento.
- Efeitos sonoros só nos motions, a -24 dB.
- Sem zoom nos cortes, sem legenda queimada, sem tela final extra.

## Rodando com o vídeo em outro computador
Se o bruto fica no computador do usuário e o Claude trabalha num ambiente na nuvem ligado a ele (shell remoto com limite de tempo por comando), veja `referencias/ambiente_remoto.md`: transcrição e motions na nuvem, render e áudio no computador, em pedaços que cabem no limite.

## Erros que já aconteceram (e a correção)
| Sintoma | Causa | Correção |
|---|---|---|
| Processo da transcrição morre sem erro | Whisper large-v3 + Chromium ao mesmo tempo (falta de RAM) | Um de cada vez |
| Gagueira continua no vídeo | O Whisper "limpa" repetições na transcrição normal | Passada de disfluências + conferência da voz editada |
| Fim de palavra comido ("diferen-") | Corte da espera começando no fim marcado pelo Whisper | `montar_cortes.py` só começa em pausa real (≥ 0,3 s) |
| Frase inteira sumiu | A transcrição pulou a frase e a "lacuna" virou espera | Lacuna com voz em > 30% do tempo não é cortada |
| Áudio escorrega no fim do vídeo | Parte com um quadro a menos | Contagem exata de quadros por parte |
| Voz 3 dB alta | Mono copiado no estéreo sem compensação | -3,01 dB ao copiar |
| Prévia do fim sem vídeo | Concat de partes que ainda não existiam | `--ultimos` usa só as partes do fim |
| Parte com desfoque passa do tempo limite | `boxblur` em 1920x1080 | Desfoque em 1/4 da resolução |
| Legenda com palavras de tomadas cortadas | Legenda montada da transcrição do bruto | `.srt` feito da transcrição da voz editada |
