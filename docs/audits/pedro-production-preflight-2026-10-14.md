# SMART360-V2 — preflight de produção de Pedro

Data: 14/10/2026. Referência: [preparação local](pedro-commercial-access-2026-10-14.md).

Atualização posterior: [SCB-PEDRO-03 — homologação PostgreSQL](SCB-PEDRO-03-postgresql.md) validou 264 testes em PostgreSQL 16.15. A versão e o inventário do destino continuam pendentes; os resultados abaixo registram o preflight anterior.

## Parecer

**NO-GO para ativação imediata em produção.** A implementação e o procedimento estão preparados para homologação; não há evidência do estado real do banco, dos usuários, dos papéis e da infraestrutura de produção. Nenhuma conexão ao banco de produção, push, deploy ou envio de senha foi realizado.

Condições para converter o parecer em GO:

1. Homologar esta revisão em PostgreSQL isolado com a mesma versão/configuração do destino, incluindo migração, provisionamento concorrente, troca de senha e rollback. A execução desta entrega usa SQLite de testes, não comprova locks/DDL em PostgreSQL.
2. Inventariar grupos, permissões diretas, memberships e identidade de Pedro no destino. Validar a alteração global de `SALESPERSON`, `VIEWER` e `CATALOG_MANAGER`; o comando recusa divergências, não as resolve silenciosamente.
3. Confirmar que a operação aceita cadastro mestre de cliente compartilhado: vendedores só editam clientes exclusivos de SMART_CONTROL e da própria carteira. Clientes compartilhados são somente leitura para vendedores; seus dados cadastrais comuns continuam visíveis a usuários com relacionamento autorizado. Não existe isolamento de campos/notas por unidade.
4. Executar backup recuperável, migração, sincronização controlada e smoke tests do runbook antes de entregar a nova credencial. Confirmar domínio, proxy HTTPS, cookies e disponibilidade de login. Nenhuma verificação remota foi feita nesta etapa.

## Auditoria do diff completo

Foram lidos o diff rastreado, todos os arquivos novos da implementação e os caminhos de autenticação, autorização, clientes, prospecção e catálogo que eles utilizam. A alteração de formatação em `src/institutional/infrastructure/django/test_commercial_refrigeration.py` é preexistente, foi preservada e deve ser excluída da release desta tarefa.

| Achado | Tratamento e impacto |
| --- | --- |
| Dashboard e auditoria compartilhavam `view_auditlog` | `view_dashboard` separado; eventos globais exigem auditoria. Sincronização altera grupos existentes; permissões diretas não são removidas. |
| Prospecção sem isolamento por usuário/unidade | Continua bloqueada para SALESPERSON. Além da remoção no grupo, autorização backend agora nega VIEW/MANAGE para vendedor não superusuário mesmo com permissões diretas ou outro grupo. Superusuários mantêm acesso administrativo. |
| Permissão composta parcialmente ausente | Checagem e diagnóstico da sincronização exigem todas as referências. |
| Filtros de clientes expunham nomes de vendedores e unidades globais | Para vendedor, opções limitadas ao próprio perfil e memberships ativos. Auditoria global de um cliente não é mais enviada a quem não possui AUDIT_VIEW. Histórico de transferência continua limitado aos relacionamentos visíveis. |
| Edição sincronizava sempre a unidade SMART_CONTROL | Vendedor só pode criar com membership OWN ativo nessa unidade e perfil ativo. Edição exige um único relacionamento, nessa unidade, atribuído ao próprio vendedor. Clientes compartilhados/outras unidades retornam 403 em GET/POST de edição. |
| Senha temporária sem fluxo anterior | `TemporaryCredential`, prazo de 24h, troca obrigatória, rejeição de senha igual, validação Django e expiração com logout. Usuários sem esse registro não são forçados a trocar. |
| Troca de senha anônima redirecionava para `/accounts/login/` inexistente | Corrigida com `LoginRequiredMixin` e a URL institucional; regressão automatizada. |
| HTML do dashboard deixava fechamento de container condicionado à auditoria | Corrigido. |
| Preparador local não era um provisionador de produção idempotente | Mantido separado; criado comando dedicado, leitura por padrão, senha nova gerada somente na criação, reexecução sem reset. |

Não foi introduzido novo RBAC. O conjunto permitido continua em `ROLE_DEFINITIONS`, com Groups/Permissions e os filtros de carteira existentes. `SALESPERSON` não constitui um teto para todas as permissões Django: concessões administrativas diretas/múltiplos grupos continuam sendo privilégios efetivos, exceto a negação explícita de prospecção. Por isso o provisionador verifica grupo exclusivo, ausência de permissões diretas, flags e único vínculo OWN. Administradores devem preservar essa política depois do provisionamento.

## Funcionalidades realmente operacionais

| Operação | Evidência/limite |
| --- | --- |
| Login, logout, sessões, CSRF, destino `next` | Rotas Django existentes; suíte de autenticação incluída. Username é o e-mail completo de Pedro, não um backend novo de login por e-mail. |
| Primeiro acesso e troca de senha | Fluxo executado em testes, incluindo senha fraca/reutilizada, expiração e navegação/API antes da troca. |
| Dashboard comercial | Contagem de clientes filtrada pela carteira, catálogo interno; não exibe logs globais nem total de vendedores ao vendedor. |
| Cadastro de clientes | Criação, consulta, pesquisa/filtros, status e edição da carteira exclusiva SMART_CONTROL; responsável fixado no próprio vendedor. POST de outro cliente não autorizado retorna 404. |
| Clientes compartilhados | Consulta do cadastro comum e relacionamentos autorizados. Edição por vendedor bloqueada. Não equivale a banco/tenant independente por vendedor. |
| Catálogo | Consulta de produtos, marcas e categorias internos; inclui itens não publicados. Mutação/publicação/imagens bloqueadas pelo backend. |
| Administração | Vendedores, unidades, equipes, departamentos, memberships e transferências negados ao perfil preparado. Django admin exige staff, que Pedro não recebe. |
| Prospecção, buscas, revisão e consolidação | Bloqueadas em todas as rotas HTML/API de Sales Intelligence, inclusive concessão direta testada. |
| Pedidos, propostas, orçamento transacional, comissões, metas, funil de oportunidades | Não identificados como fluxos implementados nos modelos/rotas comerciais auditados. Campo de modo de venda/orçamento do produto e CTAs da loja não demonstram uma gestão de propostas/pedidos. Não prometer essas funcionalidades a Pedro. |

A carteira usa `CustomerBusinessRelationship.assigned_salesperson → Salesperson.user` e membership ativo. `OWN` retorna apenas relacionamentos do vendedor nas unidades autorizadas. Foram exercitados IDOR por URL/POST, filtros, relações de outras unidades e alteração de responsável. O cadastro `Customer` é global, e os escopos ALL/TEAM/DEPARTMENT continuam disponíveis a outros perfis: não se afirma isolamento universal para contas configuradas com esses escopos.

## Migrations e usuários existentes

Única migração nova: `backoffice.0004_alter_auditlog_options_temporarycredential`, dependente de `backoffice.0003` e do modelo User configurado. Adiciona opção de permissão `view_dashboard` ao AuditLog e tabela de credencial temporária com OneToOne para User. Não migra senhas, não cria Pedro, não cria registros de credencial para usuários existentes e não sincroniza os grupos automaticamente. As permissões são criadas pelo `post_migrate` do Django; sincronizar somente depois de `migrate` concluir.

O middleware consulta a tabela para toda requisição autenticada. Publicar workers novos antes da tabela existir pode causar erro 500. Até a sincronização, usuários comuns podem perder o dashboard por não possuir `view_dashboard`. Usar janela de manutenção ou release coordenada. Não usar `--fake`.

`sync_backoffice_roles` afeta os cinco grupos gerenciados. SALESPERSON perde prospecção e auditoria; VIEWER/CATALOG_MANAGER perdem auditoria implícita; todos recebem `view_dashboard`. Gerente e administrador preservam auditoria/prospecção. Permissões externas e diretas são preservadas pelo sincronizador. Um usuário que tinha somente a permissão direta antiga de auditoria não recebe automaticamente dashboard. Revisar concessões individuais antes de liberar tráfego.

A validação local não encontrou migrations de modelo faltantes; o banco SQLite de preparação já tinha 0004 aplicada. A suíte recria a estrutura em banco de teste. Isso não confirma quais migrations estão aplicadas em produção.

## Segredos e separação de ambientes

Foi comparado o conteúdo exato da credencial temporária local com os 1.131 arquivos candidatos ao versionamento, sem imprimir a senha: **zero ocorrências**. `.env`, `db.sqlite3` e `seller-preparation.sqlite3` estavam ignorados e não rastreados; não havia arquivos staged. Adicionada regra `*.credential`. Senhas constantes nos testes são fixtures fictícias, não as credenciais geradas. Nenhuma senha foi colocada nos relatórios.

O comando de produção não importa o preparador local, não aceita senha como argumento/variável de ambiente, não lê o arquivo local e não importa SQLite. Gera `secrets.token_urlsafe(24)` no momento da criação; guarda somente hash no banco. Uma conta preexistente sem o marcador de auditoria de provisionamento de produção é recusada, inclusive se tiver sido copiada do ambiente local. Esse marcador é metadado operacional, não um mecanismo contra administrador malicioso.

Arquivo novo exige diretório privado do operador fora do checkout e é criado em modo 0600 com exclusividade. O caminho dos exemplos é apenas destino de entrega, não conteúdo a versionar. Remover o arquivo após entrega por canal seguro e troca; não anexar a tickets, logs ou PRs. Repetir verificação do diff staged antes de qualquer commit futuro; esta auditoria não garante mudanças futuras nem cobre todo o histórico Git com um scanner de segredos.

## Testes desta revisão

Execução relevante:

```bash
.venv/bin/python manage.py test src.backoffice src.customers src.salespeople src.sales_intelligence src.commerce src.institutional.infrastructure.django.tests.AuthenticationRoutesTests --settings=config.settings.local_preparation --noinput
.venv/bin/python manage.py makemigrations --check --dry-run --settings=config.settings.local_preparation
.venv/bin/python manage.py migrate --plan --settings=config.settings.local_preparation
.venv/bin/python manage.py sqlmigrate backoffice 0004 --settings=config.settings.local_preparation
git diff --check
```

Revalidação consolidada do estado atual: **262 testes passaram em 141.649 s**, em uma única execução da suíte relevante. Log local sem credenciais: `/tmp/smart360-preflight-revalidation.log`. `makemigrations --check --dry-run` não detectou mudanças faltantes; `migrate --plan` não encontrou operações pendentes no SQLite local de preparação; `git diff --check` passou. A comparação da credencial local com os 1.131 arquivos candidatos foi repetida: zero ocorrências, nenhum arquivo staged. Não foi necessário alterar a implementação nesta revalidação.

Testes novos cobrem dry-run sem geração de senha, criação/24h/hash/0600, repetição sem reset (inclusive após troca), conta local/desconhecida, drift de privilégios, credencial expirada, colisão de arquivo, rollback em falha de escrita, guarda de settings, todas as rotas de prospecção com permissões diretas, filtros/auditoria e clientes compartilhados. A primeira execução focal identificou o redirect de login incorreto e foi seguida de correção. Não houve smoke remoto, teste visual em navegador ou execução em PostgreSQL. A configuração auditada mantém cookies seguros em produção, mas MFA e throttling/lockout não foram encontrados no fluxo de login; cadastro público permanece sem atribuição de papel comercial. A proteção real do proxy e os valores efetivos de configuração precisam ser validados no destino.

## Arquivos envolvidos

- Configuração: `.gitignore`, `config/settings/base.py`, `config/settings/local_preparation.py`.
- Modelo/migração: `src/backoffice/models.py`, `src/backoffice/migrations/0004_alter_auditlog_options_temporarycredential.py`.
- RBAC/carteira: `src/backoffice/permissions/{registry,services}.py`, `src/backoffice/services/scopes.py`, `src/backoffice/views.py`.
- Credencial/rotas/templates: `src/backoffice/credentials.py`, `src/backoffice/urls.py`, `templates/backoffice/{dashboard,password_change}.html`.
- Provisionamento: `src/backoffice/management/commands/{prepare_pedro_local,provision_pedro_production}.py`, `src/backoffice/services/pedro_provisioning.py`.
- Testes: `src/backoffice/tests/{test_seller_access,test_production_preflight}.py`, `src/sales_intelligence/tests/test_sales_intelligence.py`.
- Documentos: relatório de preparação local, este parecer e [runbook de deploy/rollback](pedro-production-runbook.md).

Nenhum desses arquivos foi commitado ou enviado por esta tarefa. O relatório anterior descreve a primeira entrega; as restrições adicionais e correções deste preflight prevalecem.
