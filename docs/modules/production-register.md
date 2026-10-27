# Production Drawing Register (Drawing Log)

This optional OpenConstructionERP module is a **project-scoped production-item register**, not a CDE drawing register, manufacturing BOM, purchase order, work order or shipment execution service.

## Enable and create

Enable the `production-register` frontend plugin (disabled by default). Open a project and choose **Drawing Log** from its dashboard. The backend module is `oe_production_register` with API prefix `/api/v1/production-register`.

Creation requires both an **active, signed project contract** and a **locked, approved non-variation BOQ with a designated snapshot belonging to that BOQ**. The registered contract and snapshot IDs cannot be changed after creation. A later loss of readiness leaves data readable but blocks normal writes.

Choose one of the three start modes:

- **Empty:** create a register with the eight initial workstreams, then enter production items manually.
- **From approved BOQ:** create the register and open a panel of commercial positions. Select one or several positions, decide how to group them, and supply an internal production code. **No one-to-one item generation takes place.**
- **Import Excel:** create a register and open the XLSX wizard. Preview before committing. Importing does not mutate BOQ or other owner modules.

Each item has a stable UUID. Visible internal codes may repeat, even within one room. BOQ references are many-to-many and are resolved solely against the frozen BOQ snapshot; unresolved and ambiguous references remain visible.

## Editing and monitoring

The 20-column grid exposes original item text, quantities, BOQ mappings, a declared (nonofficial) approval date and eight configurable workstreams. Update statuses manually or in bulk; edit detailed status, source values, dates, responsible person and notes in an item's drawer. Edit organizational relations, references and audit history there. Archived items are read-only and remain accessible in history.

Internal OCERP references are same-project validated by ID for CDE, design deliverables, submittals, commercial changes, variations and scheduled activities. They are links, not duplicated documents or approvals.

## Excel round-trip

The legacy export uses 20 columns and includes a hidden `_OCERP_SYNC` worksheet. For each row this contains the originating register/item UUID, version, original identity, workstream JSON, cell hashes and schema version. Reimporting an unchanged cell preserves the structured checkpoint fields, even if the visible cell displays only a status. Editing the visible cell updates only its raw reported value; structured dates/status/responsibility are managed in OCERP. Clearing a cell clears its previous raw value. Import preview flags unresolved/ambiguous BOQ identifiers and conflicting item versions. The same file and SHA-256 must be presented to the commit endpoint.

A foreign-register synchronization identity or stale item version cannot be overridden to write into the current register. Reimport without hidden metadata relies on matching `(floor, room, item_code)` and requires an explicit decision for ambiguities.

## Middleware boundary

There are **no** PDM/MES/accounting SDKs, connectors, polling tasks, adapter credentials, integration tables or background synchronization inside this module. Other systems must integrate through middleware that invokes the authenticated OCERP REST endpoints and handles its own mapping, orchestration and transport retries. OCERP publishes local domain events only after transaction commit.

## Validation and upgrades

The implementation adds eight project-scoped tables through `backend/alembic/versions/v3325_production_register.py`. The revision in this delivery follows the upstream Alembic head `v199_subcontractor_contact_link` observed in commit `e373448829929f329cad1c81196ef722e174375c` (OCERP 18.8.2). Rebase and recalculate `down_revision` if the target branch has advanced; ensure `alembic heads` reports exactly one head before applying migrations.

Recommended checkout verification:

```bash
cd backend
ruff format --check app/modules/production_register tests/modules/test_production_register_unit.py
ruff check app/modules/production_register tests/modules/test_production_register_unit.py
pytest tests/modules/test_production_register_unit.py
pytest
alembic heads
alembic upgrade head
cd ../frontend
npm run lint
npm run build
npm test -- --run src/modules/production-register
cd ..
python scripts/check_module_manifests.py
python scripts/check_migration_heads.py
python scripts/check_repo_hygiene.py
```

**Verification qualification:** Tests run against a minimal local API-compatible shim do not prove full OCERP integration. A checkout-based PostgreSQL test, production migrations, React build and CI must be performed before production deployment. No customer document is committed with this module.
