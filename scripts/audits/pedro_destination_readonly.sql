-- SCB-PEDRO-03. Run ONLY on an explicitly authorized destination.
-- psql -X -v ON_ERROR_STOP=1 -f scripts/audits/pedro_destination_readonly.sql
-- No passwords, hashes, tokens or customer data are selected.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '3s';
SELECT current_database() AS database_name, current_setting('server_version') AS server_version,
       current_setting('transaction_read_only') AS read_only;
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolcanlogin
FROM pg_roles WHERE rolname = current_user;
SELECT app, name, applied FROM django_migrations ORDER BY app, name;
SELECT g.name AS role, count(DISTINCT ug.user_id) AS member_count,
       array_agg(DISTINCT ct.app_label || '.' || p.codename)
           FILTER (WHERE p.id IS NOT NULL) AS permissions
FROM auth_group g
LEFT JOIN auth_user_groups ug ON ug.group_id = g.id
LEFT JOIN auth_group_permissions gp ON gp.group_id = g.id
LEFT JOIN auth_permission p ON p.id = gp.permission_id
LEFT JOIN django_content_type ct ON ct.id = p.content_type_id
GROUP BY g.id, g.name ORDER BY g.name;
SELECT count(DISTINCT u.id) AS affected_accounts,
       count(DISTINCT u.id) FILTER (WHERE u.is_staff OR u.is_superuser) AS privileged_accounts,
       count(DISTINCT u.id) FILTER (WHERE EXISTS
           (SELECT 1 FROM auth_user_user_permissions up WHERE up.user_id = u.id)) AS accounts_with_direct_grants
FROM auth_user u JOIN auth_user_groups ug ON ug.user_id = u.id
JOIN auth_group g ON g.id = ug.group_id
WHERE g.name IN ('SYSTEM_ADMIN','COMMERCIAL_MANAGER','SALESPERSON','CATALOG_MANAGER','VIEWER');
WITH candidate AS (
 SELECT id, is_active, is_staff, is_superuser FROM auth_user
 WHERE lower(username) = 'pedro@smartcontrolbrasil.com.br'
    OR lower(email) = 'pedro@smartcontrolbrasil.com.br'
)
SELECT c.id AS candidate_id, c.is_active, c.is_staff, c.is_superuser,
       ARRAY(SELECT g.name FROM auth_group g JOIN auth_user_groups ug ON ug.group_id=g.id
             WHERE ug.user_id=c.id ORDER BY g.name) AS groups,
       ARRAY(SELECT ct.app_label||'.'||p.codename FROM auth_permission p
             JOIN django_content_type ct ON ct.id=p.content_type_id
             WHERE p.id IN (SELECT permission_id FROM auth_user_user_permissions WHERE user_id=c.id)
             ORDER BY ct.app_label,p.codename) AS direct_permissions
FROM candidate c;
SELECT s.id AS seller_id, s.user_id AS candidate_user_id, s.active
FROM salespeople_salesperson s
WHERE lower(s.code) = 'pedro' OR lower(s.email) = 'pedro@smartcontrolbrasil.com.br';
SELECT m.user_id AS candidate_id, b.code AS business_unit, b.is_active AS unit_active,
       m.scope, m.is_active AS membership_active, m.department_id, m.team_id
FROM backoffice_businessunitmembership m
JOIN backoffice_businessunit b ON b.id=m.business_unit_id
WHERE m.user_id IN (SELECT id FROM auth_user
 WHERE lower(username)='pedro@smartcontrolbrasil.com.br' OR lower(email)='pedro@smartcontrolbrasil.com.br');
SELECT b.code, b.is_active FROM backoffice_businessunit b WHERE b.code='SMART_CONTROL';
-- Broad/mixed scopes are counts only: do not enumerate unrelated people.
SELECT m.scope, count(*) AS salesperson_memberships
FROM backoffice_businessunitmembership m
WHERE m.user_id IN (SELECT ug.user_id FROM auth_user_groups ug
 JOIN auth_group g ON g.id=ug.group_id WHERE g.name='SALESPERSON')
GROUP BY m.scope ORDER BY m.scope;
ROLLBACK;
