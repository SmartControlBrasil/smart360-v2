# Auditoria e preparação local — Pedro — 14/10/2026

## Resultado e fronteira do trabalho

Pedro (`pedro@smartcontrolbrasil.com.br`) foi preparado **somente** no banco local descartável `seller-preparation.sqlite3`. Não foi consultado nem modificado o PostgreSQL de desenvolvimento/produção, e não houve push, deploy ou envio de credenciais. A existência de uma conta homônima em produção não foi verificada.

Foi reutilizado o RBAC baseado em `Group`, `Permission`, `SALESPERSON`, `Salesperson`, `BusinessUnitMembership` e `AccessScope.OWN`. O novo usuário é ativo, não é staff/superusuário, não possui permissões diretas e pertence exclusivamente a `SALESPERSON`. Seu vínculo está na unidade `SMART_CONTROL`; não foram atribuídos clientes reais.

## Matriz de acesso

| Recurso | Pedro |
| --- | --- |
| Dashboard | Sim, clientes filtrados pela carteira; sem auditoria global ou total de vendedores |
| Clientes | Listar, consultar, criar e editar a própria carteira dentro da unidade autorizada |
| Clientes de outros vendedores/unidades | Negado; consultas e edições por ID fora do escopo retornam 404 |
| Transferência de carteira | Negada |
| Produtos, marcas e categorias | Consulta; inclui catálogo interno, não apenas produtos publicados |
| Alteração/publicação de catálogo e imagens | Negada |
| Vendedores, unidades, departamentos, equipes, memberships | Negados |
| Usuários, permissões e Django admin | Negados |
| Auditoria global | Negada |
| Sales Intelligence / prospecção, incluindo API | Negada até implementar isolamento de registros |

## Constatações e correções

1. **Permissão de dashboard equivalia à auditoria.** `DASHBOARD_VIEW` e `AUDIT_VIEW` compartilhavam `view_auditlog`. Foi criada a permissão Django `backoffice.view_dashboard` no modelo existente, sem outro sistema de autorização. A sincronização remove a permissão de auditoria dos papéis que não a declaram.
2. **Dashboard expunha eventos globais.** Consultas e blocos de acessos/atividades agora exigem `AUDIT_VIEW`. O total de vendedores exige `SALESPEOPLE_VIEW`. Métricas de clientes continuam usando o escopo existente.
3. **Prospecção não possui isolamento por proprietário/unidade.** Views e API buscam campanhas, pesquisas, resultados e correspondências globais. Foram removidas as permissões de prospecção de `SALESPERSON`. A mudança afeta esse papel inteiro quando sincronizado; gerente comercial mantém o comportamento anterior. Não se declara esse módulo isolado para outros papéis.
4. **Permissões compostas incompletas podiam ser aceitas.** A autorização agora exige que todas as referências da permissão existam, além de todas estarem concedidas.
5. **Não havia ciclo de senha temporária.** Foi adicionado `TemporaryCredential`, validade de 24 horas e middleware que bloqueia navegação/API até a troca. Credencial expirada encerra a sessão e nega acesso. A troca usa validação e sessão do Django, exige a senha atual e rejeita reutilização da senha temporária.
6. **Sincronização preserva permissões externas por desenho.** Esse comportamento existente foi preservado. O provisionador recusa criar Pedro se `SALESPERSON` contiver permissões fora da definição esperada; não remove silenciosamente permissões externas de outros usuários.

## Autenticação auditada

O projeto usa autenticação e sessões do Django, login por `username`, hash de senha via `set_password`, validadores de senha, CSRF e validação do destino `next`. O username de Pedro é o endereço de e-mail completo, sem introduzir backend de login por e-mail. A entrada recomendada é `/login/?next=/painel/`; após a primeira autenticação a troca é obrigatória em `/painel/alterar-senha/`.

As configurações de produção declaram cookies de sessão/CSRF seguros e cabeçalho de proxy HTTPS. Não foi inspecionada a infraestrutura publicada. Não foram encontrados MFA nem throttling/lockout de login no fluxo auditado. Cadastro público continua disponível, sem atribuição automática de papel comercial. Esses pontos não foram alterados nesta etapa.

## Credencial e operação local

A senha foi gerada com `secrets.token_urlsafe(24)` (192 bits de entropia de origem), validada e armazenada no banco somente como hash. O arquivo local `/tmp/smart360-pedro-local-20261014.txt` contém a credencial e o instante exato de expiração, com modo `0600`; não contém credencial de produção. Não copiar seu conteúdo para Git, relatório ou mensagens. `/tmp` é temporário: a senha não foi entregue a Pedro e precisará ser regenerada para uma futura ativação após expirar.

Preparação reproduzível em banco isolado vazio:

```bash
.venv/bin/python manage.py migrate --settings=config.settings.local_preparation --noinput
.venv/bin/python manage.py prepare_pedro_local --settings=config.settings.local_preparation --credential-file /tmp/smart360-pedro-local-20261014.txt
.venv/bin/python manage.py runserver 127.0.0.1:8000 --settings=config.settings.local_preparation
```

O servidor não foi iniciado nesta entrega. O comando recusa outros settings/bancos, colisão de usuário/e-mail/vendedor e arquivo de credencial preexistente; uma repetição não redefine senha nem altera a conta existente. Usa transação e remove o arquivo novo se a operação falhar. O backend de e-mail local é em memória.

Uma futura implantação exige aplicar a migração `backoffice.0004` antes de servir o código e sincronizar os papéis (`sync_backoffice_roles`). **Nada disso foi executado em produção.** O provisionador desta entrega deliberadamente não funciona em produção. Uma eventual conta existente deverá ter grupos, permissões diretas, flags e memberships revisados antes da ativação, sem transportar a senha local.

## Verificação

Comando da suíte relevante:

```bash
.venv/bin/python manage.py test src.backoffice src.customers src.salespeople src.sales_intelligence --settings=config.settings.local_preparation --noinput
```

Cobertura: RBAC, dashboard, carteira própria e acesso por ID, escopos de unidades/equipes/departamentos, transferência, criação/edição de clientes, bloqueio administrativo e de prospecção, senha temporária, expiração, CSRF, validação, provisionamento e recusa de papel contaminado. Testes existentes que autorizavam vendedor na prospecção foram atualizados para a restrição explícita.

Resultado: **209 testes passaram em 142,040 s** na suíte dos quatro módulos. Após acrescentar duas regressões (permissão composta incompleta e arquivo de credencial preexistente), a suíte específica foi executada novamente: **11 testes passaram em 7,446 s**, incluindo os dois novos casos. São 211 casos distintos validados. Logs locais: `/tmp/smart360-seller-final-tests.log` e `/tmp/smart360-seller-focused-final.log`. O teste do provisionador usa override de configuração sobre o banco de testes em memória e emite o aviso esperado do Django sobre `DATABASES`; nenhum banco de produção é utilizado.

`makemigrations --check --dry-run`: nenhuma mudança ausente. `git diff --check`: sem erros. Não foi feita validação visual em navegador nem auditoria completa de infraestrutura ou de todos os módulos públicos. A alteração preexistente em `src/institutional/infrastructure/django/test_commercial_refrigeration.py` foi preservada.
