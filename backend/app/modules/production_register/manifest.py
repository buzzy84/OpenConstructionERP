"""Module manifest: optional community functionality."""
from app.core.module_loader import ModuleManifest
manifest = ModuleManifest(
    name="oe_production_register", version="1.0.0", display_name="Production Drawing Register",
    description="Project operational item register with approved BOQ baseline mappings and manual checkpoints",
    author="OpenConstructionERP Community", category="community",
    depends=["oe_projects", "oe_boq", "oe_contracts", "oe_users"],
    optional_depends=["oe_cde", "oe_design_management", "oe_submittals", "oe_changeorders", "oe_variations", "oe_schedule"],
    auto_install=False, enabled=True,
)
