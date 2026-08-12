from dataclasses import dataclass
from enum import StrEnum


class BackofficeRole(StrEnum):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    COMMERCIAL_MANAGER = "COMMERCIAL_MANAGER"
    SALESPERSON = "SALESPERSON"
    CATALOG_MANAGER = "CATALOG_MANAGER"
    VIEWER = "VIEWER"


class BackofficePermission(StrEnum):
    DASHBOARD_VIEW = "backoffice.dashboard.view"
    CUSTOMERS_VIEW = "customers.view"
    CUSTOMERS_CREATE = "customers.create"
    CUSTOMERS_UPDATE = "customers.update"
    CUSTOMERS_DELETE = "customers.delete"
    SALESPEOPLE_VIEW = "salespeople.view"
    SALESPEOPLE_MANAGE = "salespeople.manage"
    COMMERCE_PRODUCTS_VIEW = "commerce.products.view"
    COMMERCE_PRODUCTS_CREATE = "commerce.products.create"
    COMMERCE_PRODUCTS_UPDATE = "commerce.products.update"
    COMMERCE_PRODUCTS_PUBLISH = "commerce.products.publish"
    COMMERCE_PRODUCTS_DELETE = "commerce.products.delete"
    AUDIT_VIEW = "audit.view"
    USERS_MANAGE = "users.manage"
    PERMISSIONS_MANAGE = "permissions.manage"


@dataclass(frozen=True)
class DjangoPermissionRef:
    app_label: str
    codename: str

    @property
    def dotted(self):
        return f"{self.app_label}.{self.codename}"


@dataclass(frozen=True)
class RoleDefinition:
    code: BackofficeRole
    label: str
    permissions: tuple[BackofficePermission, ...]


REAL_PERMISSION_MAP = {
    BackofficePermission.DASHBOARD_VIEW: DjangoPermissionRef("backoffice", "view_auditlog"),
    BackofficePermission.CUSTOMERS_VIEW: DjangoPermissionRef("customers", "view_customer"),
    BackofficePermission.CUSTOMERS_CREATE: DjangoPermissionRef("customers", "add_customer"),
    BackofficePermission.CUSTOMERS_UPDATE: DjangoPermissionRef("customers", "change_customer"),
    BackofficePermission.SALESPEOPLE_VIEW: DjangoPermissionRef("salespeople", "view_salesperson"),
    BackofficePermission.SALESPEOPLE_MANAGE: (
        DjangoPermissionRef("salespeople", "add_salesperson"),
        DjangoPermissionRef("salespeople", "change_salesperson"),
    ),
    BackofficePermission.AUDIT_VIEW: DjangoPermissionRef("backoffice", "view_auditlog"),
}


RESERVED_PERMISSIONS = tuple(
    permission for permission in BackofficePermission if permission not in REAL_PERMISSION_MAP
)


ROLE_DEFINITIONS = {
    BackofficeRole.SYSTEM_ADMIN: RoleDefinition(
        code=BackofficeRole.SYSTEM_ADMIN,
        label="Administrador do sistema",
        permissions=tuple(BackofficePermission),
    ),
    BackofficeRole.COMMERCIAL_MANAGER: RoleDefinition(
        code=BackofficeRole.COMMERCIAL_MANAGER,
        label="Gerente comercial",
        permissions=(
            BackofficePermission.DASHBOARD_VIEW,
            BackofficePermission.CUSTOMERS_VIEW,
            BackofficePermission.CUSTOMERS_CREATE,
            BackofficePermission.CUSTOMERS_UPDATE,
            BackofficePermission.SALESPEOPLE_VIEW,
            BackofficePermission.SALESPEOPLE_MANAGE,
            BackofficePermission.COMMERCE_PRODUCTS_VIEW,
            BackofficePermission.AUDIT_VIEW,
        ),
    ),
    BackofficeRole.SALESPERSON: RoleDefinition(
        code=BackofficeRole.SALESPERSON,
        label="Vendedor",
        permissions=(
            BackofficePermission.DASHBOARD_VIEW,
            BackofficePermission.CUSTOMERS_VIEW,
        ),
    ),
    BackofficeRole.CATALOG_MANAGER: RoleDefinition(
        code=BackofficeRole.CATALOG_MANAGER,
        label="Gestor de catálogo",
        permissions=(
            BackofficePermission.DASHBOARD_VIEW,
            BackofficePermission.COMMERCE_PRODUCTS_VIEW,
            BackofficePermission.COMMERCE_PRODUCTS_CREATE,
            BackofficePermission.COMMERCE_PRODUCTS_UPDATE,
            BackofficePermission.COMMERCE_PRODUCTS_PUBLISH,
        ),
    ),
    BackofficeRole.VIEWER: RoleDefinition(
        code=BackofficeRole.VIEWER,
        label="Visualizador",
        permissions=(
            BackofficePermission.DASHBOARD_VIEW,
            BackofficePermission.CUSTOMERS_VIEW,
            BackofficePermission.SALESPEOPLE_VIEW,
            BackofficePermission.COMMERCE_PRODUCTS_VIEW,
        ),
    ),
}
