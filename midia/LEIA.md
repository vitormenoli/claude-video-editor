# midia/

Coloque aqui os arquivos do SEU canal (não vão para o repositório):

| Arquivo | Para que serve |
|---|---|
| `musica_fundo.mp3` | Música de fundo sem direitos autorais. Ela entra em loop, bem baixa (-40 LUFS nas pausas, -8 dB de ducking com voz). Use um nome sem acento. |
| `encerramento.mp4` | Vinheta/logo animada que vai sempre no final, inteira, com o próprio áudio, entrando com crossfade de 0,5 s. |
| `logo.png` | Logo do canal, se algum motion precisar. |

Os caminhos desses arquivos vão no bloco `configuracao` do `roteiro_motions.json` (`musica`, `encerramento`, `duracao_encerramento`).
Meça o volume da música uma vez com `ffmpeg -i musica_fundo.mp3 -af ebur128 -f null -` e coloque o valor "I" em `musica_lufs_original`.
