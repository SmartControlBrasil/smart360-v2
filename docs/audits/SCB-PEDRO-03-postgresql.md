# SCB-PEDRO-03 — homologação PostgreSQL e auditoria de permissões

## Parecer

**GO técnico para a homologação em PostgreSQL 16.15; NO-GO para ativar Pedro em produção.** Foram eliminadas as pendências locais de compatibilidade com PostgreSQL, migrations, autorização, concorrência do provisionador e transações. Não foi identificado um destino de produção com acesso autorizado nesta sessão. Versão, banco, migrations, usuários e permissões de produção permanecem **não verificados**. A versão instalada localmente não é evidência da versão produtiva.

Nenhum push, deploy, provisionamento ou migration de produção foi executado. Nenhum usuário existente foi alterado. Todos os dados usados nos testes foram criados sinteticamente em clusters descartáveis, sem copiar bases, clientes ou credenciais do destino. O único usuário-alvo usado pelos testes é a identidade de provisionamento já definida no código; nenhuma senha real foi importada.

Referências: [preflight anterior](pedro-production-preflight-2026-10-14.md), [runbook de implantação/rollback](pedro-production-runbook.md). Este documento atualiza a pendência de homologação daqueles relatórios; não valida o destino por inferência.

## Ambiente e versões verificadas

| Componente | Resultado |
| --- | --- |
| PostgreSQL efetivamente executado | 16.15, pacote Ubuntu `16.15-0ubuntu0.24.04.1`, x86_64 |
| Python | 3.12.3 |
| Django | 6.0.7 |
| psycopg | 3.3.4 |
| Banco exclusivo | `scb_pedro03`; banco recriado pela suíte: `test_scb_pedro03` |
| Transporte | Socket Unix em diretório `mktemp` privado `/tmp/scb-pedro-03.*`; `listen_addresses` vazio, sem TCP |
| Identidade PostgreSQL local | `scb_homologation`, criada no próprio cluster descartável |
| Dados importados | Nenhum; banco de ensaio operacional com zero usuários e zero clientes |
| Versão/banco de produção | PENDENTE; não presumidos a partir de `.env`, do hostname local ou do pacote instalado |

A autenticação `trust` é restrita ao socket dentro do diretório privado 0700 do operador; conexões TCP estão desativadas e a regra host rejeita conexões. O papel do cluster de ensaio é superusuário PostgreSQL, necessário para administrar o banco descartável de testes. **Não foi validado o conjunto mínimo de privilégios do usuário de banco de produção.** Isso não confere `is_superuser` aos usuários Django que representam vendedores.

`config.settings.postgres_homologation` usa variáveis próprias e nomes fixos de banco/papel; não utiliza `POSTGRES_HOST/DB/USER/PASSWORD`. Rejeita socket fora do padrão privado de homologação. E-mail fica em memória. O comando de provisionamento de produção não é executado contra um destino real: testes exercitam seu serviço transacional no cluster sintético e verificam a recusa de settings não produtivos no comando.

## Evidências e reprodução

Evidências sanitizadas estão em [evidence/SCB-PEDRO-03](evidence/SCB-PEDRO-03/summary.json): versões, resultados de testes, migrations, RBAC sintético e resultado do inventário somente leitura. Os arquivos não contêm passwords, hashes, tokens nem cadastros de clientes. `source-sha256.json` identifica os arquivos de implementação/testes/roteiros que foram validados; `evidence-sha256.json` permite verificar a integridade dos comprovantes.

Roteiro reproduzível, a partir da raiz do projeto, sem conexão ao destino:

```bash
bash scripts/audits/run_pedro_postgres_homologation.sh
```

Requer os binários locais em `/usr/lib/postgresql/16/bin` e `.venv` instalada. Para outra instalação, definir `SCB_PG_BIN` explicitamente. Não instala software, não baixa imagem, não usa Docker nem configura conexão remota. O roteiro cria cluster/banco exclusivos, aplica migrations, sincroniza RBAC, executa inventário sintético, roda a suíte e confere drift de migrations. O `trap` encerra o cluster ao terminar. Diretório privado e logs são preservados para diagnóstico; não distribuir nem versionar os diretórios de dados.

## Migrations e transações

- Aplicadas **34 migrations** em banco PostgreSQL vazio, incluindo `backoffice.0004_alter_auditlog_options_temporarycredential`.
- `migrate --plan` local: nenhuma operação pendente; `makemigrations --check --dry-run`: nenhuma mudança faltante.
- Sincronizados os cinco grupos existentes no desenho RBAC; nenhuma permissão requerida ausente.
- Teste PostgreSQL reverte 0004 para 0003, confirma ausência da tabela temporária, reaplica 0004 e confirma a tabela e preservação de um usuário sintético preexistente. A migração não cria credencial temporária para esse usuário.
- Duas conexões concorrentes ao PostgreSQL chamam o provisionador: uma retorna `created`, a outra `unchanged`; existe um usuário, um membership, uma credencial e um único arquivo de entrega. A senha permanece a inicialmente gerada. Isso valida `select_for_update` no grupo para provisionadores cooperantes.
- Falha de escrita do arquivo faz rollback de usuário/vínculos e remove o arquivo novo. Arquivo existente nunca é sobrescrito; conta divergente, permissões externas e credencial expirada causam recusa sem modificação.
- Idempotência após troca de senha também foi testada: repetição não substitui a senha pessoal nem reinicia o prazo.

A reversão de schema foi testada apenas em banco descartável. Não é recomendação para remover 0004 de uma produção ativa: isso destruiria o estado das credenciais e quebraria o middleware novo. O bloqueio concorrente entre provisionadores não impede um administrador de mudar permissões simultaneamente; continua necessária a janela sem mudanças concorrentes de RBAC.

## Testes executados

Primeira execução PostgreSQL: **262 testes aprovados em 99,935 s**. Em seguida, **2 testes exclusivos de PostgreSQL aprovados em 1,291 s**, validando concorrência e reversão/reaplicação de schema.

Roteiro completo executado de ponta a ponta: **264 testes aprovados em 90.963 s**, saída 0; cluster encerrado pelo próprio roteiro. Esse total inclui os dois testes exclusivos de PostgreSQL. Não houve skips de PostgreSQL nessa execução.

Escopo: `backoffice`, `customers`, `salespeople`, `sales_intelligence`, `commerce` e `AuthenticationRoutesTests` institucional. Não são todos os testes institucionais/visuais do repositório. Os testes de autenticação incluem troca obrigatória, expiração em 24 horas, rejeição de senha fraca/igual, CSRF e invalidação da senha temporária. Os testes transacionais exclusivos não são substituídos por SQLite; usam `TransactionTestCase` e conexões separadas reais.

## Matriz de segurança validada no backend

| Operação | Perfil preparado de vendedor |
| --- | --- |
| Login/logout, troca de senha e sessão | Operacionais; credencial temporária exige troca, expirada encerra a sessão |
| Dashboard | Carteira própria, sem auditoria global nem total de vendedores |
| Carteira por lista, busca, URL direta e POST | Somente relacionamentos OWN autorizados; cliente alheio não é recuperado por ID |
| Criação/edição de cliente exclusivo SMART_CONTROL | Permitida ao perfil ativo com membership OWN; POST de outro responsável não altera atribuição |
| Cliente compartilhado ou fora da unidade padrão | Edição GET/POST bloqueada; consulta do cadastro comum quando há relacionamento autorizado |
| Catálogo interno | Leitura; criação, edição, publicação e imagens bloqueadas |
| Administração, usuários, memberships, transferências e Django admin | Negados ao perfil sem staff/superuser/permissões diretas |
| Prospecção | Todas as rotas HTML/API negadas mesmo com permissões diretas de Sales Intelligence |
| Tentativa de ampliar privilégios pelo provisionador | Recusa de conta/grupo/membership divergente; não adota conta privilegiada nem importa credencial local |

Método não suportado pode retornar 405 antes de verificar permissão; métodos de consulta/mutação suportados negados retornam 403. Clientes fora do escopo retornam 404. A suite verifica respostas e persistência nos casos de alteração.

O RBAC Django é aditivo: a presença de SALESPERSON não retira privilégios administrativos concedidos explicitamente por outro grupo ou diretamente, exceto a negação específica de prospecção. A política validada exige um único grupo, nenhum grant direto, flags administrativas falsas e único membership OWN. A interface disponível a Pedro não permite editar esses atributos; administradores externos ao perfil ainda podem mudá-los. Portanto é indispensável conferir a configuração efetiva no destino antes da ativação.

O cadastro mestre `Customer` continua compartilhado. O isolamento confirmado é o acesso à carteira por relacionamento; não existe isolamento de campos/notas entre unidades quando o mesmo cliente é compartilhado. A edição pelo vendedor nesses casos é bloqueada. Cadastros compartilhados podem ser consultados por quem possui relacionamento autorizado; essa limitação exige aceite operacional.

## Auditoria READ-ONLY do destino

**Não executada em produção por falta de destino/acesso autorizado identificado.** Foi solicitada apenas a identificação do meio de acesso, sem pedir senhas ou tokens. Na ausência de informação, não foram tentadas conexões com credenciais encontradas por inferência.

| Verificação de produção | Estado |
| --- | --- |
| Host/banco/versão PostgreSQL | Não verificados |
| Migrations efetivamente aplicadas | Não verificadas |
| Grupos/permissões diretas/roles de banco | Não verificados |
| Existência de Pedro e conflitos de username/e-mail/perfil | Não verificados |
| Memberships, unidade SMART_CONTROL ativa e escopos | Não verificados |
| Impacto concreto em outras contas | Não quantificado |
| Proxy HTTPS, cookies, dependências instaladas e login publicado | Não verificados remotamente |

Preparado e testado **somente no banco sintético**: `scripts/audits/pedro_destination_readonly.sql`. Usa `BEGIN READ ONLY`, timeouts e `ROLLBACK`; seleciona versão/banco, migrations, grupos e permissões, contagens de contas impactadas, grants diretos, candidatos a Pedro e memberships, sem hashes, tokens ou clientes. O inventário sintético apresenta cinco grupos RBAC, zero membros e zero conflitos — **não é o inventário de produção**.

Quando houver acesso autorizado, o operador pode executar com conexão de auditoria já estabelecida, sem senha na linha de comando:

```bash
psql -X -v ON_ERROR_STOP=1 -f scripts/audits/pedro_destination_readonly.sql
```

Esse exemplo não define destino nem credencial. Se schema/tabelas não existirem, a transação falha: registrar o desvio, não aplicar migrations para “consertar” durante a auditoria. Guardar a saída em local privado e revisar antes de compartilhar. O roteiro de homologação já passou parâmetros explícitos do socket sintético para ensaiar o mesmo SQL.

## Impactos e riscos remanescentes

1. A versão real do servidor produtivo pode diferir de 16.15. Se diferir de forma relevante, repetir homologação na versão correspondente antes de GO.
2. A migração precisa existir antes de iniciar workers com o middleware. A sincronização troca o acesso ao dashboard para `view_dashboard`, retira auditoria implícita de vendedor/viewer/catalog manager e retira prospecção de vendedores; preserva grants externos/diretos. Usuários que dependiam desses grants requerem revisão individual no destino.
3. Não foi medido o volume produtivo, tempo de migration sob carga, bloqueios de DDL, permissões do papel da aplicação nem mudanças concorrentes de administração.
4. MFA/throttling não foram identificados no fluxo auditado; configuração real de proxy e proteção de login precisa ser conferida no destino. Nenhuma promessa de validação integral de infraestrutura.
5. O cadastro compartilhado e o RBAC aditivo têm os limites descritos acima. Não liberar prospecção até existir isolamento de objetos apropriado.
6. Reemissão de credencial expirada/perdida é uma operação separada, explícita e auditada; o provisionador idempotente não renova automaticamente. O segredo local anterior nunca é reutilizado.

## Plano final de implantação e rollback

O [runbook anterior](pedro-production-runbook.md) continua sendo o procedimento detalhado. Ordem exigida após resolver o NO-GO:

1. Obter identificação e acesso autorizado READ-ONLY ao destino; executar inventário, confirmar versão/schema e revisar conflitos/impactos. Não misturar essa fase com escritas.
2. Validar aceite dos limites de cliente compartilhado, backup recuperável e privilégios necessários do papel de aplicação. Repetir o ensaio na versão do destino se necessário.
3. Em futura janela autorizada de implantação: manutenção das rotas autenticadas, aplicar migrations revisadas, sincronizar RBAC, executar dry-run do provisionador e revisar resultado.
4. Só então, em operação explicitamente autorizada, criar Pedro com `--apply` e arquivo privado externo. Geração de senha nova, 24h e troca obrigatória; sem copiar conta/SQLite/credencial da homologação.
5. Smoke tests do runbook: login/troca, carteira própria e cliente alheio, cliente compartilhado, catálogo, administração/prospecção negadas, sessão de gerente existente, repetição idempotente e ausência de 500. Entrega do segredo somente por canal seguro após gates.
6. Rollback preferencial: suspender acesso de Pedro, invalidar senha/sessões e desativar membership/perfil, preservando clientes e auditoria. Não apagar usuário/dados para contornar conflitos. Se retornar código antigo, suspender todos os usuários com troca pendente e manter o painel indisponível para vendedores até preservar os bloqueios de segurança. Não sincronizar cegamente papéis antigos nem reverter 0004 com workers novos ativos.

**Decisão final:** homologação local PostgreSQL concluída; ativação produtiva permanece **NO-GO** pelos itens de destino não verificados, não por falha da suíte PostgreSQL. Nenhuma etapa de implantação/rollback produtivo foi executada.

## Entrega e commit local

Arquivos novos desta fase: settings PostgreSQL isolado, roteiro reproduzível, SQL de auditoria READ-ONLY, testes de concorrência/DDL, este relatório e evidências sanitizadas. O commit local também inclui a implementação SALESPERSON e os testes/documentos das etapas anteriores que estavam pendentes e são dependências necessárias desta homologação. A alteração preexistente em `test_commercial_refrigeration.py` é excluída.

Verificação final de segredo: 1.145 arquivos candidatos comparados à credencial local anterior, zero ocorrências; `.env`, bancos SQLite e `*.credential` ignorados e não rastreados. Não versionar `.env`, bancos SQLite, dados do cluster, arquivos `.credential` ou logs brutos privados. Commit apenas local, sem publicação. Consultar `git log -1` para o identificador efetivo após o commit; o conteúdo do relatório não depende de um hash autorreferente.
