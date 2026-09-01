# Smart360 Prospect Chrome Extension

V1 operacional para auxiliar prospecção no Google Maps e enviar resultados visíveis para o Smart360 Sales Intelligence.

## Arquitetura

- `manifest.json`: Manifest V3, permissões mínimas e hosts autorizados.
- `background.js`: controla estado, abas, lotes, retry, dedupe local e chamadas Smart360.
- `content/google_maps.js`: roda somente no Google Maps, detecta feed/cards, extrai dados e faz scroll progressivo.
- `popup/`: interface simples para configurar URL, SearchRun ID, busca e comandos.
- `lib/smart360_api.js`: cliente centralizado das APIs internas do Smart360.

## Como carregar no Chrome

1. Abra `chrome://extensions`.
2. Ative `Modo do desenvolvedor`.
3. Clique em `Carregar sem compactação`.
4. Selecione `browser_extensions/smart360_prospecting`.
5. Fixe a extensão na barra do Chrome, se desejar.

## Configuração Smart360

No popup, informe a URL base:

- DEV: `http://127.0.0.1:8000`
- Alternativa local: `http://localhost:8000`
- PROD: `https://www.smartcontrolbrasil.com.br`

A URL base não é segredo. Não há token, senha ou API key fixa na extensão.

## Autenticação e CSRF

A V1 usa a autenticação web existente do Smart360:

1. Abra o Smart360 no mesmo Chrome.
2. Faça login normalmente.
3. Garanta que o cookie `csrftoken` exista para a URL base.
4. A extensão envia `credentials: "include"` e lê o cookie `csrftoken` via permissão `cookies`, restrita aos hosts declarados no manifest.

Não foi adicionado `csrf_exempt`, não foi habilitado `CORS_ALLOW_ALL_ORIGINS` e não há liberação para qualquer `chrome-extension://` arbitrário.

Em produção, se o Django rejeitar a origem `chrome-extension://<extension-id>` nas chamadas mutáveis, autorize somente o ID publicado da extensão, de forma explícita e documentada. Não autorize wildcard.

## Como criar SearchRun

A V1 usa a abordagem mais simples: o usuário informa manualmente o `SearchRun ID` no popup.

O SearchRun precisa existir e estar `RUNNING`. Ele pode ser criado pelo backoffice/API atual do Smart360 antes de iniciar a coleta.

## Como iniciar uma busca

1. Faça login no Smart360.
2. Tenha uma `SearchRun` em status `RUNNING`.
3. Abra o popup da extensão.
4. Informe URL base, `SearchRun ID` e a busca, por exemplo `hospital Campinas SP`.
5. Clique em `Iniciar`.
6. A extensão abre ou reutiliza uma aba do Google Maps e inicia a coleta progressiva.

## Pausar, retomar, finalizar e cancelar

- `Pausar`: para o scroll/coleta no Google Maps, mas não cancela a SearchRun.
- `Retomar`: reinicia a coleta na aba do Maps mantida no estado local.
- `Finalizar`: envia pendentes confirmados por ACK e chama `POST complete`.
- `Cancelar`: chama `POST cancel` no Smart360.

## Estratégia Google Maps

A extensão evita classes CSS ofuscadas e concentra o acesso ao DOM em funções como:

- `getResultsFeed()`
- `getVisibleCards()`
- `extractBusinessFromCard()`
- `getScrollTarget()`

A coleta prioriza roles, `aria-label`, links para `/maps/place/` e `cid` quando disponíveis. Quando o DOM do Maps mudar, a manutenção esperada é ajustar essas funções concentradas.

## Dados extraídos

A V1 tenta obter:

- `name` obrigatório;
- `phone` quando visível no card;
- `website` quando há link externo visível;
- `address`, `city`, `state` por texto visível;
- `source_url` do link do Maps;
- `external_id` somente quando há `cid` claro na URL;
- `raw_data` com categoria, rating, avaliações, trecho de texto e versão do coletor.

A V1 não clica agressivamente em detalhes de cada estabelecimento. Se telefone/site não estiverem no card visível, podem ficar vazios. Não há enriquecimento externo.

## Deduplicação, batch e retry

A deduplicação local usa, em ordem:

1. `external_id`;
2. `source_url`;
3. `name + phone`;
4. `name + address`;
5. `name` como fallback conservador.

O envio usa buffer de 10 resultados. Um resultado só é marcado como enviado depois de ACK HTTP do Smart360. Retry limitado usa backoff simples de 1s, 2s e 5s. Em falha definitiva, a coleta fica pausada ou falha com mensagem no popup.

## Condições de parada

Valores centralizados em `content/google_maps.js`:

- `requested_limit` atingido;
- fim da lista detectado;
- 6 ciclos sem novas empresas;
- usuário pausa/para;
- timeout máximo de 12 minutos;
- página deixa de ser Google Maps.

## Depuração

O logging é controlado por `DEBUG = false` nos scripts. Para investigar, altere localmente para `true` e observe logs com prefixo `[Smart360 Prospect]` no DevTools.

## Checklist manual

1. Autenticar no Smart360.
2. Criar campanha.
3. Criar SearchRun em status `RUNNING`.
4. Carregar extensão unpacked no Chrome.
5. Abrir popup.
6. Configurar URL base do Smart360.
7. Informar SearchRun ID.
8. Informar `hospital Campinas SP`.
9. Clicar `Iniciar`.
10. Observar aba do Google Maps abrir/rolar.
11. Observar contador de encontrados/enviados subir.
12. Verificar `SearchResult` no backoffice.
13. Clicar `Pausar`.
14. Clicar `Retomar`.
15. Clicar `Finalizar`.
16. Conferir status da SearchRun e resultados em `/painel/sales-intelligence/revisao/`.

## Limitações conhecidas

- Google Maps muda DOM sem aviso; os seletores precisarão manutenção eventual.
- Não há evasão de CAPTCHA, bloqueio, rate-limit ou validação da plataforma.
- Não há CNPJ, e-mail, pessoas, LinkedIn, score, WhatsApp, CSV, Celery, Redis, n8n, Places API, Selenium ou Playwright.
- Telefone/site dependem do que estiver visível no card nesta V1.
- Retomada após reboot do Chrome é básica: estado local persiste, mas não há recuperação perfeita do content script.
