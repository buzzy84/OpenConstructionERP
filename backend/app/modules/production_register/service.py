"""All writes remain inside OCERP; no adapters, polling or external services."""
from __future__ import annotations
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any
from fastapi import HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.events import publish_after_commit
from app.modules.boq.models import BOQ, BOQSnapshot
from app.modules.boq.quantity_baseline import designated_baseline_id
from app.modules.contracts.models import Contract
from app.modules.projects.models import Project
from .models import ProductionRegister, ProductionItem, ItemBOQLink, ItemRelation, WorkstreamDefinition, ItemCheckpoint, ItemReference, RegisterAudit
from .repository import ProductionRegisterRepository
from .schemas import RegisterCreate, ItemInput, ItemPatch, BOQLinkInput, CheckpointWrite, ReferenceCreate, WorkstreamCreate

INITIAL_WORKSTREAMS = (
    ("production", "Production", "production", "PRODUZIONE"),
    ("glass", "Glass", "external", "VETRERIA"),
    ("lighting", "Lighting", "external", "ILLUMINAZIONE"),
    ("finishes", "Fabrics, Wallcoverings, Stone", "external", "TESSUTI, CARTE, PIETRA"),
    ("marble", "Marble", "external", "MARMO"),
    ("hardware", "Hardware", "external", "FERRAMENTA"),
    ("shipment_1", "Shipment 1", "shipping", "SPEDIZIONE 1"),
    ("shipment_2", "Shipment 2", "shipping", "SPEDIZIONE 2"),
)


def fail(status: int, code: str, message: str) -> None:
    raise HTTPException(status, detail={"code": code, "message_key": f"production_register.errors.{code.lower()}", "message": message, "violations": []})


def serialize(obj: Any) -> dict[str, Any]:
    return {col.name: _jsonable(getattr(obj, col.name)) for col in obj.__table__.columns}


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class RegisterService:
    def __init__(self, session: AsyncSession, project_id: uuid.UUID, actor_id: uuid.UUID):
        self.db, self.project_id, self.actor_id = session, project_id, actor_id
        self.repo = ProductionRegisterRepository(session)

    async def readiness(self) -> dict:
        project = await self.db.get(Project, self.project_id)
        if project is None or project.status in ("archived", "deleted"):
            fail(404, "PROJECT_NOT_FOUND", "Project not available")
        contracts = list((await self.db.execute(select(Contract).where(Contract.project_id == self.project_id, Contract.status == "active", Contract.signed_at.is_not(None)))).scalars())
        bills = list((await self.db.execute(select(BOQ).where(BOQ.project_id == self.project_id, BOQ.variation_request_id.is_(None), BOQ.is_locked.is_(True), BOQ.approved_at.is_not(None), BOQ.approved_by.is_not(None)))).scalars())
        eligible = []
        for bill in bills:
            snapshot_id = designated_baseline_id(bill)
            if snapshot_id is None:
                continue
            snap = await self.db.get(BOQSnapshot, snapshot_id)
            if snap is not None and snap.boq_id == bill.id:
                eligible.append({"id": str(bill.id), "name": bill.name, "snapshot_id": str(snapshot_id)})
        reasons = []
        if not contracts:
            reasons.append("SIGNED_ACTIVE_CONTRACT_REQUIRED")
        if not eligible:
            reasons.append("APPROVED_BOQ_BASELINE_REQUIRED")
        current = await self.repo.register(self.project_id)
        return {"can_create": not reasons and current is None, "reasons": reasons,
                "eligible_contracts": [{"id": str(c.id), "code": c.code} for c in contracts],
                "eligible_boqs": eligible, "register_id": str(current.id) if current else None}

    async def require_register(self, *, write: bool = False) -> ProductionRegister:
        register = await self.repo.register(self.project_id, for_update=write)
        if register is None:
            fail(404, "REGISTER_NOT_FOUND", "Drawing log not created")
        if write:
            if register.state != "active":
                fail(409, "REGISTER_ARCHIVED", "Register is archived")
            ready = await self.readiness()
            if not any(c["id"] == str(register.contract_id) for c in ready["eligible_contracts"]):
                fail(409, "CONTRACT_NOT_READY", "Contract no longer active and signed")
            if not any(b["id"] == str(register.boq_id) and b["snapshot_id"] == str(register.baseline_snapshot_id) for b in ready["eligible_boqs"]):
                fail(409, "BOQ_NOT_READY", "Approved BOQ baseline is no longer eligible")
        return register

    async def create(self, inp: RegisterCreate) -> ProductionRegister:
        # Lock the project row so two simultaneous creates cannot both pass the
        # existence check before the register's UNIQUE(project_id) constraint.
        locked_project = (await self.db.execute(select(Project.id).where(
            Project.id == self.project_id).with_for_update())).scalar_one_or_none()
        if locked_project is None:
            fail(404, "PROJECT_NOT_FOUND", "Project not found")
        ready = await self.readiness()
        if ready["register_id"]:
            fail(409, "REGISTER_EXISTS", f"Register exists: {ready['register_id']}")
        if inp.contract_id not in [uuid.UUID(c["id"]) for c in ready["eligible_contracts"]]:
            fail(409, "CONTRACT_NOT_READY", "Choose an active signed project contract")
        choice = next((b for b in ready["eligible_boqs"] if b["id"] == str(inp.boq_id)), None)
        if choice is None:
            fail(409, "BOQ_NOT_READY", "Choose an approved project BOQ with a valid baseline")
        row = ProductionRegister(project_id=self.project_id, contract_id=inp.contract_id, boq_id=inp.boq_id,
                                 baseline_snapshot_id=uuid.UUID(choice["snapshot_id"]), created_by=self.actor_id, created_mode=inp.mode)
        self.db.add(row)
        await self.db.flush()
        for index, (code, label, category, legacy) in enumerate(INITIAL_WORKSTREAMS):
            self.db.add(WorkstreamDefinition(register_id=row.id, project_id=self.project_id, code=code,
                       label=label, category=category, legacy_column=legacy, sort_order=index))
        self.audit(row, "register", row.id, "created", after={"contract_id": str(inp.contract_id), "boq_id": str(inp.boq_id)})
        self.event(row, "register.created")
        await self.db.flush()
        return row

    def audit(self, register: ProductionRegister, kind: str, entity_id: uuid.UUID, action: str, *, before: dict | None = None,
              after: dict | None = None, reason: str | None = None, source: str = "api") -> None:
        self.db.add(RegisterAudit(project_id=self.project_id, register_id=register.id, entity_kind=kind,
                    entity_id=entity_id, action=action, actor_id=self.actor_id, source=source,
                    before=before or {}, after=after or {}, reason=reason, occurred_at=datetime.now(UTC)))

    def event(self, reg: ProductionRegister, action: str, *, item_id: uuid.UUID | None = None) -> None:
        name = f"production_register.{action}"
        payload = {"event_id": str(uuid.uuid4()), "schema_version": 1, "project_id": str(self.project_id),
                   "register_id": str(reg.id), "item_id": str(item_id) if item_id else None,
                   "version": reg.version, "occurred_at": datetime.now(UTC).isoformat(), "actor_id": str(self.actor_id), "action": action}
        publish_after_commit(self.db, name, payload, source_module="oe_production_register")

    async def bump(self, reg: ProductionRegister) -> None:
        reg.version += 1
        await self.db.flush()

    async def require_item(self, reg: ProductionRegister, item_id: uuid.UUID) -> ProductionItem:
        row = await self.repo.item(reg.id, self.project_id, item_id)
        if row is None:
            fail(404, "ITEM_NOT_FOUND", "Item not found in this project")
        return row

    @staticmethod
    def check_version(actual: int, expected: int) -> None:
        if actual != expected:
            fail(409, "VERSION_CONFLICT", f"Expected version {expected}, current version {actual}")

    async def boq_positions(self, reg: ProductionRegister) -> list[dict]:
        snap = await self.db.get(BOQSnapshot, reg.baseline_snapshot_id)
        if snap is None or snap.boq_id != reg.boq_id:
            fail(409, "BASELINE_MISSING", "Pinned baseline is not available")
        return list(snap.snapshot_data.get("positions") or [])

    async def replace_links(self, reg: ProductionRegister, item: ProductionItem, links: list[BOQLinkInput]) -> list[ItemBOQLink]:
        positions = await self.boq_positions(reg)
        by_ref: dict[str, list[dict]] = defaultdict(list)
        for pos in positions:
            by_ref[str(pos.get("ordinal", ""))].append(pos)
        seen: set[str] = set()
        created = []
        for order, link in enumerate(links):
            raw = link.boq_ref_raw.strip()
            if not raw or raw in seen:
                fail(422, "DUPLICATE_BOQ_REF", f"Blank or duplicate BOQ reference: {raw}")
            seen.add(raw)
            matches = by_ref.get(raw, [])
            if link.boq_position_id is not None:
                if not any(str(p.get("id")) == str(link.boq_position_id) and str(p.get("ordinal")) == raw for p in matches):
                    fail(422, "INVALID_BOQ_POSITION", "The selected position is not in the immutable approved baseline")
                resolution, position_id = "resolved", link.boq_position_id
            elif len(matches) == 1:
                resolution, position_id = "resolved", uuid.UUID(str(matches[0]["id"]))
            else:
                resolution, position_id = ("ambiguous" if matches else "unresolved"), None
            created.append(ItemBOQLink(project_id=self.project_id, item_id=item.id, boq_id=reg.boq_id,
                        baseline_snapshot_id=reg.baseline_snapshot_id, boq_ref_raw=raw, boq_position_id=position_id,
                        resolution=resolution, sort_order=order))
        for old in await self.repo.links(item.id):
            await self.db.delete(old)
        self.db.add_all(created)
        await self.db.flush()
        return created

    async def add_item(self, reg: ProductionRegister, inp: ItemInput, *, origin: str = "manual") -> ProductionItem:
        attrs = inp.model_dump(exclude={"boq_links"})
        item = ProductionItem(register_id=reg.id, project_id=self.project_id, origin=origin, **attrs)
        self.db.add(item)
        await self.db.flush()
        if inp.boq_links:
            await self.replace_links(reg, item, inp.boq_links)
        await self.bump(reg)
        self.audit(reg, "item", item.id, "created", after=serialize(item))
        self.event(reg, "item.created", item_id=item.id)
        return item

    async def edit_item(self, reg: ProductionRegister, item: ProductionItem, inp: ItemPatch) -> ProductionItem:
        self.check_version(item.version, inp.expected_version)
        before = serialize(item)
        nonnullable = {"item_code", "floor", "room", "category", "description", "specification",
                       "comments", "change_notes", "notes", "scope"}
        for name, val in inp.model_dump(exclude_unset=True, exclude={"expected_version"}).items():
            if name in nonnullable and val is None:
                fail(422, "INVALID_ITEM_FIELD", f"{name} cannot be null")
            setattr(item, name, val)
        item.version += 1
        await self.bump(reg)
        self.audit(reg, "item", item.id, "updated", before=before, after=serialize(item))
        self.event(reg, "item.updated", item_id=item.id)
        return item

    async def put_checkpoint(self, reg: ProductionRegister, item: ProductionItem, workstream: WorkstreamDefinition, inp: CheckpointWrite):
        if workstream.register_id != reg.id:
            fail(404, "WORKSTREAM_NOT_FOUND", "Workstream not in project")
        check = (await self.db.execute(select(ItemCheckpoint).where(ItemCheckpoint.item_id == item.id,
                     ItemCheckpoint.workstream_id == workstream.id).with_for_update())).scalar_one_or_none()
        current = check.version if check else 0
        self.check_version(current, inp.expected_version)
        old = serialize(check) if check else {}
        if check is None:
            check = ItemCheckpoint(project_id=self.project_id, item_id=item.id, workstream_id=workstream.id)
            self.db.add(check)
        for key, value in inp.model_dump(exclude={"expected_version"}).items():
            setattr(check, key, value)
        check.updated_by = self.actor_id
        check.source = "api"
        check.version = current + 1
        await self.db.flush()
        await self.bump(reg)
        self.audit(reg, "checkpoint", check.id, "changed", before=old, after=serialize(check))
        self.event(reg, "checkpoint.changed", item_id=item.id)
        return check

    async def validate_reference(self, ref: ReferenceCreate) -> None:
        if ref.kind == "external":
            return
        # Owner-side validation without new dependencies or external calls.
        # Import owner models on demand: optional packages may not be installed.
        from app.modules.cde.models import DocumentContainer
        from app.modules.design_management.models import DesignDeliverable
        from app.modules.submittals.models import Submittal
        from app.modules.changeorders.models import ChangeOrder
        from app.modules.variations.models import VariationRequest
        from app.modules.schedule.models import Activity, Schedule
        owner = {"cde_container": DocumentContainer, "design_deliverable": DesignDeliverable,
                 "submittal": Submittal, "change_order": ChangeOrder, "variation_request": VariationRequest,
                 "schedule_activity": Activity}[ref.kind]
        if ref.kind == "schedule_activity":
            statement = (select(Activity.id).join(Schedule, Activity.schedule_id == Schedule.id)
                         .where(Activity.id == ref.owner_id, Schedule.project_id == self.project_id))
        else:
            statement = select(owner.id).where(owner.id == ref.owner_id, owner.project_id == self.project_id)
        found = (await self.db.execute(statement)).scalar_one_or_none()
        if found is None:
            fail(404, "REFERENCE_NOT_FOUND", "Referenced OCERP record not in this project")

    async def details(self, reg: ProductionRegister, item: ProductionItem) -> dict:
        result = serialize(item)
        result["boq_links"] = [serialize(x) for x in await self.repo.links(item.id)]
        result["checkpoints"] = [serialize(x) for x in await self.repo.checkpoints(item.id)]
        result["relations"] = [serialize(x) for x in await self.repo.relations(item.id)]
        result["references"] = [serialize(x) for x in await self.repo.references(item.id)]
        return result

    async def summary(self, reg: ProductionRegister) -> dict:
        items = list((await self.db.execute(select(ProductionItem).where(ProductionItem.register_id == reg.id,
                     ProductionItem.lifecycle != "archived"))).scalars())
        by_floor = Counter(x.floor for x in items)
        by_category = Counter(x.category for x in items)
        links = list((await self.db.execute(select(ItemBOQLink).join(ProductionItem, ItemBOQLink.item_id == ProductionItem.id)
                   .where(ProductionItem.register_id == reg.id, ProductionItem.lifecycle != "archived"))).scalars())
        checks = list((await self.db.execute(select(ItemCheckpoint).join(ProductionItem, ItemCheckpoint.item_id == ProductionItem.id)
                    .where(ProductionItem.register_id == reg.id, ProductionItem.lifecycle != "archived"))).scalars())
        return {"item_count": len(items), "unresolved_boq_links": sum(x.resolution != "resolved" for x in links),
                "distinct_boq_positions": len({x.boq_position_id for x in links if x.boq_position_id}),
                "by_floor": dict(by_floor), "by_category": dict(by_category),
                "checkpoint_status": dict(Counter(c.status for c in checks))}
