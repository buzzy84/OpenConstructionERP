"""Reuse OCERP permission registry and role ordering."""
from app.core.permissions import Role, permission_registry

def register_permissions() -> None:
    permission_registry.register_module_permissions("production_register", {
        "production_register.read": Role.VIEWER,
        "production_register.edit": Role.EDITOR,
        "production_register.import": Role.EDITOR,
        "production_register.export": Role.VIEWER,
        "production_register.manage": Role.MANAGER,
    })
