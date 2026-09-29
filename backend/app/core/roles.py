"""System role definitions used across authorization checks."""


class RoleName:
    OWNER = "owner"  # full control of the tenant (created at registration)
    MANAGER = "manager"  # everything except user/company administration
    SALESPERSON = "salesperson"  # CRM + inventory day-to-day work
    ACCOUNTANT = "accountant"  # payments, invoices, financial reports
    SERVICE = "service"  # service appointments & vehicle servicing
    VIEWER = "viewer"  # read-only across the tenant


ALL_ROLES: tuple[str, ...] = (
    RoleName.OWNER,
    RoleName.MANAGER,
    RoleName.SALESPERSON,
    RoleName.ACCOUNTANT,
    RoleName.SERVICE,
    RoleName.VIEWER,
)

ROLE_LEVELS: dict[str, int] = {
    RoleName.VIEWER: 10,
    RoleName.SERVICE: 20,
    RoleName.ACCOUNTANT: 30,
    RoleName.SALESPERSON: 40,
    RoleName.MANAGER: 80,
    RoleName.OWNER: 100,
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    RoleName.OWNER: "Company owner - full access including administration",
    RoleName.MANAGER: "Manages operations, inventory, staff workload",
    RoleName.SALESPERSON: "Works leads, offers and vehicle sales",
    RoleName.ACCOUNTANT: "Handles payments, invoices and financial reports",
    RoleName.SERVICE: "Handles service appointments and maintenance",
    RoleName.VIEWER: "Read-only access to company data",
}
