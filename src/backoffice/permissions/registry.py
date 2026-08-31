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
    CUSTOMERS_TRANSFER_ASSIGNMENT = "customers.transfer_assignment"
    CUSTOMERS_DELETE = "customers.delete"
    SALESPEOPLE_VIEW = "salespeople.view"
    SALESPEOPLE_MANAGE = "salespeople.manage"
    COMMERCE_PRODUCTS_VIEW = "commerce.products.view"
    COMMERCE_PRODUCTS_CREATE = "commerce.products.create"
    COMMERCE_PRODUCTS_UPDATE = "commerce.products.update"
    COMMERCE_PRODUCTS_PUBLISH = "commerce.products.publish"
    COMMERCE_PRODUCTS_DELETE = "commerce.products.delete"
    COMMERCE_CATEGORIES_VIEW = "commerce.categories.view"
    COMMERCE_CATEGORIES_CREATE = "commerce.categories.create"
    COMMERCE_CATEGORIES_UPDATE = "commerce.categories.update"
    COMMERCE_BRANDS_VIEW = "commerce.brands.view"
    COMMERCE_BRANDS_CREATE = "commerce.brands.create"
    COMMERCE_BRANDS_UPDATE = "commerce.brands.update"
    COMMERCE_IMAGES_VIEW = "commerce.images.view"
    COMMERCE_IMAGES_CREATE = "commerce.images.create"
    COMMERCE_IMAGES_UPDATE = "commerce.images.update"
    COMMERCE_IMAGES_DELETE = "commerce.images.delete"
    AUDIT_VIEW = "audit.view"
    BUSINESS_UNITS_VIEW = "business_units.view"
    BUSINESS_UNITS_CREATE = "business_units.create"
    BUSINESS_UNITS_UPDATE = "business_units.update"
    DEPARTMENTS_VIEW = "departments.view"
    DEPARTMENTS_CREATE = "departments.create"
    DEPARTMENTS_UPDATE = "departments.update"
    TEAMS_VIEW = "teams.view"
    TEAMS_CREATE = "teams.create"
    TEAMS_UPDATE = "teams.update"
    BUSINESS_UNIT_MEMBERSHIPS_VIEW = "business_unit_memberships.view"
    BUSINESS_UNIT_MEMBERSHIPS_CREATE = "business_unit_memberships.create"
    BUSINESS_UNIT_MEMBERSHIPS_UPDATE = "business_unit_memberships.update"
    USERS_MANAGE = "users.manage"
    PERMISSIONS_MANAGE = "permissions.manage"
    SALES_INTELLIGENCE_VIEW = "sales_intelligence.view"
    SALES_INTELLIGENCE_MANAGE = "sales_intelligence.manage"


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
    BackofficePermission.CUSTOMERS_TRANSFER_ASSIGNMENT: DjangoPermissionRef("customers", "transfer_customerassignment"),
    BackofficePermission.SALESPEOPLE_VIEW: DjangoPermissionRef("salespeople", "view_salesperson"),
    BackofficePermission.SALESPEOPLE_MANAGE: (
        DjangoPermissionRef("salespeople", "add_salesperson"),
        DjangoPermissionRef("salespeople", "change_salesperson"),
    ),
    BackofficePermission.COMMERCE_PRODUCTS_VIEW: DjangoPermissionRef("commerce", "view_product"),
    BackofficePermission.COMMERCE_PRODUCTS_CREATE: DjangoPermissionRef("commerce", "add_product"),
    BackofficePermission.COMMERCE_PRODUCTS_UPDATE: DjangoPermissionRef("commerce", "change_product"),
    BackofficePermission.COMMERCE_CATEGORIES_VIEW: DjangoPermissionRef("commerce", "view_category"),
    BackofficePermission.COMMERCE_CATEGORIES_CREATE: DjangoPermissionRef("commerce", "add_category"),
    BackofficePermission.COMMERCE_CATEGORIES_UPDATE: DjangoPermissionRef("commerce", "change_category"),
    BackofficePermission.COMMERCE_BRANDS_VIEW: DjangoPermissionRef("commerce", "view_brand"),
    BackofficePermission.COMMERCE_BRANDS_CREATE: DjangoPermissionRef("commerce", "add_brand"),
    BackofficePermission.COMMERCE_BRANDS_UPDATE: DjangoPermissionRef("commerce", "change_brand"),
    BackofficePermission.COMMERCE_IMAGES_VIEW: DjangoPermissionRef("commerce", "view_productimage"),
    BackofficePermission.COMMERCE_IMAGES_CREATE: DjangoPermissionRef("commerce", "add_productimage"),
    BackofficePermission.COMMERCE_IMAGES_UPDATE: DjangoPermissionRef("commerce", "change_productimage"),
    BackofficePermission.COMMERCE_IMAGES_DELETE: DjangoPermissionRef("commerce", "delete_productimage"),
    BackofficePermission.AUDIT_VIEW: DjangoPermissionRef("backoffice", "view_auditlog"),
    BackofficePermission.BUSINESS_UNITS_VIEW: DjangoPermissionRef("backoffice", "view_businessunit"),
    BackofficePermission.BUSINESS_UNITS_CREATE: DjangoPermissionRef("backoffice", "add_businessunit"),
    BackofficePermission.BUSINESS_UNITS_UPDATE: DjangoPermissionRef("backoffice", "change_businessunit"),
    BackofficePermission.DEPARTMENTS_VIEW: DjangoPermissionRef("backoffice", "view_department"),
    BackofficePermission.DEPARTMENTS_CREATE: DjangoPermissionRef("backoffice", "add_department"),
    BackofficePermission.DEPARTMENTS_UPDATE: DjangoPermissionRef("backoffice", "change_department"),
    BackofficePermission.TEAMS_VIEW: DjangoPermissionRef("backoffice", "view_team"),
    BackofficePermission.TEAMS_CREATE: DjangoPermissionRef("backoffice", "add_team"),
    BackofficePermission.TEAMS_UPDATE: DjangoPermissionRef("backoffice", "change_team"),
    BackofficePermission.BUSINESS_UNIT_MEMBERSHIPS_VIEW: DjangoPermissionRef("backoffice", "view_businessunitmembership"),
    BackofficePermission.BUSINESS_UNIT_MEMBERSHIPS_CREATE: DjangoPermissionRef("backoffice", "add_businessunitmembership"),
    BackofficePermission.BUSINESS_UNIT_MEMBERSHIPS_UPDATE: DjangoPermissionRef("backoffice", "change_businessunitmembership"),
    BackofficePermission.SALES_INTELLIGENCE_VIEW: (
        DjangoPermissionRef("sales_intelligence", "view_marketsegment"),
        DjangoPermissionRef("sales_intelligence", "view_prospectingcampaign"),
        DjangoPermissionRef("sales_intelligence", "view_searchrun"),
        DjangoPermissionRef("sales_intelligence", "view_searchresult"),
        DjangoPermissionRef("sales_intelligence", "view_campaignprospect"),
    ),
    BackofficePermission.SALES_INTELLIGENCE_MANAGE: (
        DjangoPermissionRef("sales_intelligence", "add_prospectingcampaign"),
        DjangoPermissionRef("sales_intelligence", "change_prospectingcampaign"),
        DjangoPermissionRef("sales_intelligence", "add_searchrun"),
        DjangoPermissionRef("sales_intelligence", "change_searchrun"),
        DjangoPermissionRef("sales_intelligence", "add_searchresult"),
        DjangoPermissionRef("sales_intelligence", "change_searchresult"),
        DjangoPermissionRef("sales_intelligence", "add_campaignprospect"),
        DjangoPermissionRef("sales_intelligence", "change_campaignprospect"),
    ),
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
            BackofficePermission.CUSTOMERS_TRANSFER_ASSIGNMENT,
            BackofficePermission.SALESPEOPLE_VIEW,
            BackofficePermission.SALESPEOPLE_MANAGE,
            BackofficePermission.COMMERCE_PRODUCTS_VIEW,
            BackofficePermission.COMMERCE_PRODUCTS_UPDATE,
            BackofficePermission.COMMERCE_CATEGORIES_VIEW,
            BackofficePermission.COMMERCE_BRANDS_VIEW,
            BackofficePermission.AUDIT_VIEW,
            BackofficePermission.BUSINESS_UNITS_VIEW,
            BackofficePermission.DEPARTMENTS_VIEW,
            BackofficePermission.TEAMS_VIEW,
            BackofficePermission.BUSINESS_UNIT_MEMBERSHIPS_VIEW,
            BackofficePermission.SALES_INTELLIGENCE_VIEW,
            BackofficePermission.SALES_INTELLIGENCE_MANAGE,
        ),
    ),
    BackofficeRole.SALESPERSON: RoleDefinition(
        code=BackofficeRole.SALESPERSON,
        label="Vendedor",
        permissions=(
            BackofficePermission.DASHBOARD_VIEW,
            BackofficePermission.CUSTOMERS_VIEW,
            BackofficePermission.CUSTOMERS_CREATE,
            BackofficePermission.CUSTOMERS_UPDATE,
            BackofficePermission.COMMERCE_PRODUCTS_VIEW,
            BackofficePermission.COMMERCE_CATEGORIES_VIEW,
            BackofficePermission.COMMERCE_BRANDS_VIEW,
            BackofficePermission.SALES_INTELLIGENCE_VIEW,
            BackofficePermission.SALES_INTELLIGENCE_MANAGE,
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
            BackofficePermission.COMMERCE_CATEGORIES_VIEW,
            BackofficePermission.COMMERCE_CATEGORIES_CREATE,
            BackofficePermission.COMMERCE_CATEGORIES_UPDATE,
            BackofficePermission.COMMERCE_BRANDS_VIEW,
            BackofficePermission.COMMERCE_BRANDS_CREATE,
            BackofficePermission.COMMERCE_BRANDS_UPDATE,
            BackofficePermission.COMMERCE_IMAGES_VIEW,
            BackofficePermission.COMMERCE_IMAGES_CREATE,
            BackofficePermission.COMMERCE_IMAGES_UPDATE,
            BackofficePermission.COMMERCE_IMAGES_DELETE,
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
            BackofficePermission.COMMERCE_CATEGORIES_VIEW,
            BackofficePermission.COMMERCE_BRANDS_VIEW,
        ),
    ),
}
