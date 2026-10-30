# Rodando com o vídeo no computador do usuário e o Claude na nuvem

Foi assim que os primeiros vídeos foram editados: o Claude trabalha num ambiente na nuvem (com internet limitada, Python, FFmpeg e Playwright) ligado ao computador do usuário pelo app do Claude, que dá um shell remoto nas pastas conectadas.

## Limites do shell remoto
- Cada comando morre em **45 s**, e processos em segundo plano morrem junto com o comando.
- Sem internet.
- Não pode apagar arquivos, só criar e sobrescrever (peça ao usuário para apagar).

## Divisão do trabalho
| Onde | O quê |
|---|---|
| Nuvem | transcrições (Whisper), cortes, planejamento, render dos motions (Playwright), folha de contato, legenda |
| Computador | extração do áudio, áudio em etapas (`cortar`, `medir`, `tratar`, `mixar`, `codificar`, uma por comando), render das partes de 40 s (uma por comando, ~15 a 25 s cada), junção final e conferências |

## Levar e trazer arquivos
- **Computador → nuvem:** `device_stage_files` (até 400 MB por arquivo). Leve só o `voz_16k.flac`, nunca o bruto inteiro.
- **Nuvem → computador:** junte num `.zip`, envie com `SendUserFile` (o usuário recebe um card; avise que é arquivo de trabalho), grave com `device_commit_files` (até 20 MB por arquivo) e extraia com `python3 -c "import zipfile; zipfile.ZipFile('x.zip').extractall('.')"`.
- Caminhos: no `device_stage_files`/`device_commit_files` use o caminho do Windows (`C:\Users\...`); no shell remoto, `~/mnt/<pasta>`; no `plano.json`, o caminho absoluto do shell remoto (`/sessions/<sessão>/mnt/<pasta>/...`).

## Dicas
- Para ver um quadro do bruto, gere um JPG pequeno no computador (`ffmpeg -ss T -i bruto.mp4 -frames:v 1 -vf scale=960:540 q.jpg`) e traga com `device_stage_files`.
- Nomes de arquivo com acento podem vir em NFD e o caminho literal falha: use cópias sem acento.
- O `freezedetect` em 1080p não cabe em 45 s: rode em pedaços de 140 s com `scale=480:270`.
