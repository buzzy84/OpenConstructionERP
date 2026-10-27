"""Production register plugin entry point."""

async def on_startup() -> None:
    from .permissions import register_permissions
    register_permissions()
