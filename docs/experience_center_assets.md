# Smart360 Experience Center Assets

| ID | Categoria | Finalidade | Formato esperado | Dimensao/duracao sugerida | Nome sugerido | Origem/licenca | Status | Uso |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| click-ui | audio | Feedback de clique | MP3/OGG | 0.1s a 0.3s | click-ui.mp3 | A definir | Pendente | `audio.map.click` |
| points-earned | audio | Pontuacao recebida | MP3/OGG | 0.3s a 0.8s | points-earned.mp3 | A definir | Pendente | feedback `+XP` |
| achievement-unlocked | audio | Conquista desbloqueada | MP3/OGG | 0.8s a 1.5s | achievement-unlocked.mp3 | A definir | Pendente | `experience:achievement-unlocked` |
| mission-complete | audio | Missao concluida | MP3/OGG | 0.8s a 1.5s | mission-complete.mp3 | A definir | Pendente | `experience:mission-completed` |
| level-up | audio | Passagem de nivel | MP3/OGG | 1s a 2s | level-up.mp3 | A definir | Pendente | `experience:level-up` |
| liro-intro | audio | Voz de introducao do Liro | MP3/OGG | 4s a 10s | liro-intro.mp3 | A definir | Pendente | acao `meet-liro` |
| liro-help | audio | Voz de ajuda do Liro | MP3/OGG | 3s a 8s | liro-help.mp3 | A definir | Pendente | ajuda contextual futura |
| mission-icon | icone | Identificar missoes | SVG/WebP | 64x64 | mission-icon.svg | A definir | Pendente | painel de missoes |
| achievement-icon | icone | Identificar conquistas | SVG/WebP | 64x64 | achievement-icon.svg | A definir | Pendente | notificacao de conquista |
| xp-icon | icone | Representar XP | SVG/WebP | 48x48 | xp-icon.svg | A definir | Pendente | HUD |
| audio-icon | icone | Botao de audio | SVG/WebP | 32x32 | audio-icon.svg | A definir | Pendente | toggle de audio |
| success-animation | animacao | Sucesso de interacao | JSON/WebM/CSS | ate 2s | success-animation.json | A definir | Pendente | feedback visual |
| unlock-animation | animacao | Desbloqueio de conquista | JSON/WebM/CSS | ate 3s | unlock-animation.json | A definir | Pendente | conquista |
| map-background | imagem | Fundo do mapa da experiencia | WebP/AVIF | 1920x1080 | map-background.webp | A definir | Pendente | area principal |
| liro-avatar | imagem | Avatar/personagem Liro | WebP/PNG | 800x800 | liro-avatar.webp | A definir | Pendente | card Liro |
| particles | imagem/animacao | Particulas discretas | SVG/CSS/WebP | variavel | particles.svg | A definir | Pendente | camada decorativa controlada |
| technical-video | video | Conteudo tecnico demonstrativo | MP4/WebM | 15s a 60s | technical-video.mp4 | A definir | Pendente | interacoes futuras |

Para substituir placeholders, coloque os arquivos finais na subpasta correspondente em
`static/institutional/experience-center/` e ajuste apenas `experience-config.js`.
