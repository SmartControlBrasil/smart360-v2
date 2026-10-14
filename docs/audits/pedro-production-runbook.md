# Runbook — acesso comercial de Pedro

**Preparado, não executado.** Usar somente após satisfazer o [parecer de preflight](pedro-production-preflight-2026-10-14.md). Não contém senha. Os comandos de produção abaixo destinam-se ao operador em uma janela futura autorizada.

Homologação local executada e evidências: [SCB-PEDRO-03](SCB-PEDRO-03-postgresql.md). A homologação em PostgreSQL 16.15 passou; confirmar equivalência da versão e inventariar o destino antes de executar os passos produtivos deste runbook.

## Login

Caminho: `/login/?next=/painel/`. URL esperada conforme domínio institucional configurado: `https://www.smartcontrolbrasil.com.br/login/?next=/painel/` — confirmar o host efetivamente publicado antes de enviar. Login: `pedro@smartcontrolbrasil.com.br`. Troca: `/painel/alterar-senha/`. Dashboard: `/painel/`.

## Preparação e inventário

1. Separar somente os arquivos desta tarefa; excluir a alteração preexistente de refrigeração. Revisar `git diff --cached` e verificar que `.env`, SQLite, arquivos `.credential`, dumps e logs não entram no artefato. Não copiar `/tmp/smart360-pedro-local-20261014.txt` nem `seller-preparation.sqlite3`.
2. Homologar em PostgreSQL isolado. Usar credencial própria da homologação e descartar o banco ao terminar; nunca transportar seus usuários/credenciais ao destino.
3. No destino, identificar a revisão anterior e salvar backup completo com restauração ensaiada. Guardar inventário de grupos/permissões diretas/memberships em armazenamento privado; não publicar dump de auth_user (contém hashes) no repositório. Verificar colisões de username/e-mail de Pedro sem diferenciar maiúsculas e de vendedor código PEDRO/e-mail; revisar contas com múltiplos grupos e escopos amplos.
4. Confirmar unidade `SMART_CONTROL` ativa, ambiente correto, segredo Django e HTTPS. Registrar o plano de migrations e verificar se há migrations pendentes de outros módulos: `migrate` pode aplicar mais que 0004. Não prosseguir sem revisar essa lista.

```bash
.venv/bin/python manage.py showmigrations --settings=config.settings.production
.venv/bin/python manage.py migrate --plan --settings=config.settings.production
.venv/bin/python manage.py check --deploy --settings=config.settings.production
```

Não executar esses comandos com apontamento de produção durante desenvolvimento/preflight local. A identificação e o backup do servidor dependem da infraestrutura e não foram inferidos nesta entrega.

## Deploy coordenado

1. Ativar manutenção das rotas autenticadas e suspender writes concorrentes de administração de RBAC enquanto sincroniza/provisiona. Instalar a revisão e dependências validadas, mantendo os workers antigos parados ou isolados do tráfego.
2. Aplicar a migração e sincronizar papéis. Registrar saída e comparar permissões com inventário anterior. O sincronizador preserva permissões externas; removê-las exige revisão específica, não automatização deste procedimento.

```bash
.venv/bin/python manage.py migrate --settings=config.settings.production --noinput
.venv/bin/python manage.py sync_backoffice_roles --settings=config.settings.production
.venv/bin/python manage.py provision_pedro_production --settings=config.settings.production
```

O último comando é **somente leitura por padrão**. Resultados possíveis: seria criado, já corresponde à política (nenhuma mudança), ou erro de precondição. Não criar ou “adotar” uma conta divergente, local ou sem marcador. Resolver identidade, grupos e vínculos com responsável administrativo, fora deste automatismo, antes de tentar novamente.

3. Só com preflight válido, criar diretório privado fora do checkout (exemplo abaixo; ajustar dono/caminho ao usuário do processo), provisionar e iniciar workers da nova revisão:

```bash
install -d -m 700 /var/lib/smart360-private
.venv/bin/python manage.py provision_pedro_production --settings=config.settings.production --apply --credential-file /var/lib/smart360-private/pedro-initial.credential
```

A aplicação é transacional, não sincroniza todos os grupos nem cria unidades. Na criação: usuário ativo, sem staff/superuser/permissões diretas, somente SALESPERSON, perfil ativo PEDRO, um membership OWN em SMART_CONTROL; senha nova com validade de 24h contada da geração. O arquivo é exclusivo, 0600, sem senha em stdout/auditoria. Transação PostgreSQL bloqueia a linha do grupo para serializar provisionadores cooperantes; isso não substitui a janela sem mudanças administrativas concorrentes.

**Idempotência:** repetir o mesmo comando depois de sucesso valida a política e retorna sem alterar senha, prazo, grupos, perfil ou vínculos, mesmo se o arquivo já existir. Após troca pessoal, não recria senha temporária. Divergência ou credencial ainda pendente porém expirada causa erro sem reset. Falha durante escrita desfaz o banco e remove o arquivo recém-criado; encerramento abrupto pode deixar arquivo órfão. Nesse caso, conferir banco e arquivo privadamente antes de qualquer remoção/reexecução.

**Expiração/perda do arquivo:** não há renovação automática nem opção de importar senha. Não apagar e recriar o usuário para contornar a guarda. Suspender acesso e abrir procedimento explícito de reemissão que gere novo segredo, faça `set_password`, atualize prazo/must_change e registre auditoria, após validar novamente a identidade e os vínculos. Esse procedimento de recuperação não foi executado nem automatizado nesta entrega.

4. Validar sessão administrativa e conta sem credencial temporária. Executar smoke tests; liberar tráfego e entregar credencial privadamente somente após todos os gates. Não usar logs HTTP com corpos de login/senha. Monitorar 403/500 e erros de tabela/permissão sem capturar credenciais.

## Smoke tests

Executar o ensaio completo em homologação com clientes de teste de Pedro, outro vendedor, outra unidade e um cliente compartilhado. Em produção, usar apenas registros autorizados e registrar IDs/status, nunca senha ou dados cadastrais no relatório.

| Teste | Esperado |
| --- | --- |
| Anônimo GET `/painel/` e `/painel/alterar-senha/` | 302 para login institucional existente |
| Login temporário válido | Redirecionamento para troca antes de qualquer painel/API |
| Senha fraca, igual à temporária ou POST sem CSRF | Erro de validação/403; acesso continua bloqueado |
| Troca pessoal válida | Dashboard disponível; senha temporária anterior falha |
| Logout | POST com CSRF encerra sessão |
| Login após 24h sem troca | Requisição autenticada seguinte nega 403 e encerra sessão; ensaiar expiração em homologação sem alterar relógio de produção |
| GET dashboard/clientes | Só carteira própria; sem logs globais nem opções de outros vendedores/unidades |
| Criar cliente e editar cliente próprio exclusivo SMART_CONTROL | Sucesso; atribuição permanece ao próprio vendedor mesmo com tentativa de outro responsável no POST |
| GET/POST cliente alheio por ID, busca e filtros | Sem resultado/404; nenhuma alteração |
| Editar cliente compartilhado ou vinculado somente a outra unidade | 403; dados/relacionamentos não alterados |
| GET catálogo | 200; leitura interna de produtos/marcas/categorias |
| POST produto/ativação/imagem e GET/POST administração | 403, nenhum efeito no banco |
| `/admin/` com Pedro | Redireciona ao login administrativo; acesso de staff negado |
| GET campanhas/revisão e API de pesquisa; POST criação/finalização/vínculo | 403 após troca; método não suportado pode retornar 405. Nunca 2xx |
| Repetir provisionamento | “Nenhuma alteração”, mesmo prazo e hash (não imprimir hash) |
| Gerente/admin existente e usuário sem TemporaryCredential | Acesso previsto preservado, sem troca forçada acidental |

## Rollback

Preferir **rollback do acesso**, preservando as correções de segurança, a tabela e a auditoria. Manter manutenção enquanto há incerteza.

1. Se a falha ocorreu antes de criar Pedro, não há conta a remover. Investigar migração/RBAC sob manutenção e reaplicar correção; não entregar credencial.
2. Se Pedro foi criado por este provisionador, suspendê-lo sem apagar perfil, clientes ou histórico. Exemplo para operador executar com a nova revisão e settings de produção, após conferir identidade/marcador:

```bash
.venv/bin/python manage.py shell --settings=config.settings.production <<'PY'
from django.contrib.auth import get_user_model
from django.db import transaction
from src.backoffice.models import AuditLog, TemporaryCredential
from src.backoffice.services.pedro_provisioning import EMAIL, PROVISIONING_MARKER
from src.salespeople.models import Salesperson

with transaction.atomic():
    user = get_user_model().objects.select_for_update().get(username=EMAIL, email=EMAIL)
    if not AuditLog.objects.filter(object_type="User", object_id=str(user.pk), metadata__provisioning=PROVISIONING_MARKER).exists():
        raise RuntimeError("Origem divergente: parar e revisar")
    if user.is_active:
        user.is_active = False
        user.set_unusable_password()
        user.save(update_fields=["is_active", "password"])
        user.groups.clear()
        user.user_permissions.clear()
        user.business_unit_memberships.update(is_active=False)
        Salesperson.objects.filter(user=user).update(active=False)
        AuditLog.objects.create(action=AuditLog.Action.DEACTIVATE, module="backoffice", object_type="User", object_id=str(user.pk), object_repr=EMAIL, metadata={"reason": "production-access-rollback"})
print("Acesso de Pedro suspenso; nenhuma senha exibida.")
PY
```

A troca para senha inutilizável invalida o hash de sessão do Django; `is_active=False` impede nova autenticação no backend padrão. Repetir o rollback não altera uma conta já suspensa. Remover o arquivo de entrega em armazenamento privado após confirmar a suspensão. Não deletar todos os usuários/sessões ou dados comerciais.

3. Se for indispensável retornar o código anterior: antes, suspender **todos** os usuários com `TemporaryCredential.must_change=True`, não só Pedro, pois o código antigo ignora expiração/troca obrigatória. Preservar a tabela 0004 e os dados. Coordenar inventário e restauração de RBAC por grupo/permissão; **não executar cegamente o sincronizador antigo**, pois ele reintroduz prospecção para vendedores. O dashboard antigo também não contém as correções de exposição: manter `/painel/` indisponível aos vendedores até aplicar uma correção segura. Um rollback de código não reverte permissões automaticamente.
4. Não reverter 0004 durante operação normal: isso destrói o estado das credenciais e quebra o middleware novo. Reversão de schema, se realmente necessária, só após desligar todos os workers novos, suspender usuários pendentes e validar backup/restauração em homologação. A permissão criada via `post_migrate` não é restaurada/removida com a semântica de grupos automaticamente. Não usar `migrate ... --fake` como rollback.
5. Restaurar backup completo apenas em cenário de recuperação aprovado e com reconciliação das escritas posteriores; não sobrepor produção ativa. Registrar revisão, horário, ações e validação de acesso suspenso, sem hashes/senhas.
