"""Project-scoped, permissioned OCERP API for the production drawing register."""
from __future__ import annotations
import uuid
from datetime import UTC, datetime
from io import BytesIO
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_, delete
from app.dependencies import CurrentUserId, SessionDep, RequirePermission, verify_project_access
from .models import ProductionItem, WorkstreamDefinition, ItemCheckpoint, ItemBOQLink, ItemRelation, ItemReference, RegisterAudit
from .schemas import (RegisterCreate, ItemInput, ItemPatch, ArchiveRequest, BOQLinksReplace,
                      RelationsReplace, WorkstreamCreate, WorkstreamPatch, CheckpointWrite,
                      CheckpointBulk, ReferenceCreate)
from .service import RegisterService, serialize, fail

router = APIRouter(tags=["production_register"])
READ = Depends(RequirePermission("production_register.read"))
EDIT = Depends(RequirePermission("production_register.edit"))
IMPORT = Depends(RequirePermission("production_register.import"))
EXPORT = Depends(RequirePermission("production_register.export"))
MANAGE = Depends(RequirePermission("production_register.manage"))
PREFIX = "/projects/{project_id}/drawing-log"

async def svc(session: SessionDep, project_id: uuid.UUID, user_id: CurrentUserId) -> RegisterService:
    await verify_project_access(project_id, str(user_id), session)
    return RegisterService(session, project_id, uuid.UUID(str(user_id)))

@router.get("/projects/{project_id}/readiness", dependencies=[READ])
async def readiness(s: RegisterService = Depends(svc)):
    return await s.readiness()

@router.post(PREFIX, dependencies=[EDIT], status_code=201)
async def create(data: RegisterCreate, s: RegisterService = Depends(svc)):
    return serialize(await s.create(data))

@router.get(PREFIX, dependencies=[READ])
async def get_register(s: RegisterService = Depends(svc)):
    reg = await s.require_register()
    return {**serialize(reg), "workstreams": [serialize(w) for w in await s.repo.workstreams(reg.id)]}

@router.get(PREFIX + "/boq-candidates", dependencies=[READ])
async def boq_candidates(s: RegisterService = Depends(svc)):
    reg = await s.require_register()
    return {"items": await s.boq_positions(reg)}

@router.get(PREFIX + "/items", dependencies=[READ])
async def list_items(s: RegisterService = Depends(svc), page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=200),
                     search: str | None = None, floor: str | None = None, room: str | None = None, category: str | None = None,
                     item_code: str | None = None, boq_ref: str | None = None, lifecycle: str | None = "active",
                     checkpoint_status: str | None = None):
    reg = await s.require_register()
    q = select(ProductionItem).where(ProductionItem.register_id == reg.id, ProductionItem.project_id == s.project_id)
    if lifecycle:
        q = q.where(ProductionItem.lifecycle == lifecycle)
    for column, val in ((ProductionItem.floor, floor), (ProductionItem.room, room), (ProductionItem.category, category), (ProductionItem.item_code, item_code)):
        if val:
            q = q.where(column == val)
    if search:
        q = q.where(or_(ProductionItem.item_code.ilike(f"%{search}%"), ProductionItem.description.ilike(f"%{search}%"), ProductionItem.room.ilike(f"%{search}%")))
    if boq_ref:
        q = q.where(ProductionItem.id.in_(select(ItemBOQLink.item_id).where(ItemBOQLink.boq_ref_raw.ilike(f"%{boq_ref}%"))))
    if checkpoint_status:
        q = q.where(ProductionItem.id.in_(select(ItemCheckpoint.item_id).where(ItemCheckpoint.status == checkpoint_status)))
    count = (await s.db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = list((await s.db.execute(q.order_by(ProductionItem.display_order, ProductionItem.created_at)
                   .offset((page - 1) * page_size).limit(page_size))).scalars())
    ids = [x.id for x in rows]
    links = list((await s.db.execute(select(ItemBOQLink).where(ItemBOQLink.item_id.in_(ids)))).scalars()) if ids else []
    checks = list((await s.db.execute(select(ItemCheckpoint).where(ItemCheckpoint.item_id.in_(ids)))).scalars()) if ids else []
    grouped_links, grouped_checks = {}, {}
    for l in links:
        grouped_links.setdefault(l.item_id, []).append(serialize(l))
    for c in checks:
        grouped_checks.setdefault(c.item_id, []).append(serialize(c))
    return {"page": page, "page_size": page_size, "total": count, "items": [
        {**serialize(x), "boq_links": grouped_links.get(x.id, []), "checkpoints": grouped_checks.get(x.id, [])} for x in rows]}

@router.post(PREFIX + "/items", dependencies=[EDIT], status_code=201)
async def add_item(data: ItemInput, s: RegisterService = Depends(svc)):
    reg = await s.require_register(write=True)
    return await s.details(reg, await s.add_item(reg, data))

@router.get(PREFIX + "/items/{item_id}", dependencies=[READ])
async def item_detail(item_id: uuid.UUID, s: RegisterService = Depends(svc)):
    reg = await s.require_register()
    return await s.details(reg, await s.require_item(reg, item_id))

@router.patch(PREFIX + "/items/{item_id}", dependencies=[EDIT])
async def edit_item(item_id: uuid.UUID, data: ItemPatch, s: RegisterService = Depends(svc)):
    reg = await s.require_register(write=True)
    return serialize(await s.edit_item(reg, await s.require_item(reg, item_id, write=True), data))

@router.post(PREFIX + "/items/{item_id}/archive", dependencies=[MANAGE])
async def archive_item(item_id: uuid.UUID, data: ArchiveRequest, s: RegisterService = Depends(svc)):
    reg = await s.require_register(write=True)
    item = await s.require_item(reg, item_id)
    s.check_version(item.version, data.expected_version)
    if item.lifecycle == "archived":
        fail(409, "ALREADY_ARCHIVED", "Item already archived")
    before = serialize(item)
    item.lifecycle, item.archived_at, item.version = "archived", datetime.now(UTC), item.version + 1
    await s.bump(reg)
    s.audit(reg, "item", item.id, "archived", before=before, after=serialize(item), reason=data.reason)
    s.event(reg, "item.archived", item_id=item.id)
    return serialize(item)

@router.put(PREFIX + "/items/{item_id}/boq-links", dependencies=[EDIT])
async def put_boq_links(item_id: uuid.UUID, data: BOQLinksReplace, s: RegisterService = Depends(svc)):
    reg = await s.require_register(write=True)
    item = await s.require_item(reg, item_id, write=True)
    s.check_version(item.version, data.expected_version)
    before = [serialize(x) for x in await s.repo.links(item.id)]
    links = await s.replace_links(reg, item, data.links)
    item.version += 1
    await s.bump(reg)
    s.audit(reg, "item", item.id, "boq_links_changed", before={"links": before}, after={"links": [serialize(x) for x in links]})
    s.event(reg, "item.boq_links_changed", item_id=item.id)
    return {"item_version": item.version, "items": [serialize(l) for l in links]}

@router.put(PREFIX + "/items/{item_id}/relations", dependencies=[EDIT])
async def put_relations(item_id: uuid.UUID, data: RelationsReplace, s: RegisterService = Depends(svc)):
    reg = await s.require_register(write=True)
    item = await s.require_item(reg, item_id, write=True)
    s.check_version(item.version, data.expected_version)
    existing = list((await s.db.execute(select(ItemRelation).where(ItemRelation.project_id == s.project_id,
                  ItemRelation.parent_item_id.in_(select(ProductionItem.id).where(ProductionItem.register_id == reg.id))))).scalars())
    new_edges = [(r.child_item_id, r.kind) for r in data.relations]
    if len(new_edges) != len(set(new_edges)) or any(child == item.id for child, _ in new_edges):
        fail(422, "INVALID_RELATION", "Duplicate or self-referential item relation")
    for child, _ in new_edges:
        await s.require_item(reg, child)
    edges: dict[uuid.UUID, set[uuid.UUID]] = {}
    for rel in existing:
        if rel.parent_item_id != item.id and rel.kind == "contains":
            edges.setdefault(rel.parent_item_id, set()).add(rel.child_item_id)
    edges[item.id] = {child for child, kind in new_edges if kind == "contains"}
    def cyclic(node: uuid.UUID, seen: set[uuid.UUID], path: set[uuid.UUID]) -> bool:
        if node in path: return True
        if node in seen: return False
        seen.add(node)
        return any(cyclic(child, seen, path | {node}) for child in edges.get(node, set()))
    visited: set[uuid.UUID] = set()
    if any(cyclic(node, visited, set()) for node in edges):
        fail(422, "CONTAINS_CYCLE", "Containment must be acyclic")
    before = [serialize(x) for x in existing if x.parent_item_id == item.id]
    for old in existing:
        if old.parent_item_id == item.id:
            await s.db.delete(old)
    fresh = [ItemRelation(project_id=s.project_id, parent_item_id=item.id, child_item_id=child,
                          kind=kind, created_by=s.actor_id) for child, kind in new_edges]
    s.db.add_all(fresh)
    await s.db.flush()
    item.version += 1
    await s.bump(reg)
    s.audit(reg, "item", item.id, "relations_changed", before={"relations": before}, after={"relations": [serialize(x) for x in fresh]})
    s.event(reg, "item.updated", item_id=item.id)
    return {"item_version": item.version, "items": [serialize(x) for x in fresh]}

@router.get(PREFIX + "/workstreams", dependencies=[READ])
async def workstreams(s: RegisterService = Depends(svc)):
    reg = await s.require_register()
    return {"items": [serialize(w) for w in await s.repo.workstreams(reg.id)]}

@router.post(PREFIX + "/workstreams", dependencies=[MANAGE], status_code=201)
async def add_workstream(data: WorkstreamCreate, s: RegisterService = Depends(svc)):
    reg = await s.require_register(write=True)
    if any(w.code == data.code for w in await s.repo.workstreams(reg.id)):
        fail(409, "DUPLICATE_WORKSTREAM", "Workstream code already exists")
    row = WorkstreamDefinition(project_id=s.project_id, register_id=reg.id, **data.model_dump())
    s.db.add(row)
    await s.db.flush()
    await s.bump(reg)
    s.audit(reg, "workstream", row.id, "created", after=serialize(row))
    s.event(reg, "item.updated")
    return serialize(row)

@router.patch(PREFIX + "/workstreams/{workstream_id}", dependencies=[MANAGE])
async def edit_workstream(workstream_id: uuid.UUID, data: WorkstreamPatch, s: RegisterService = Depends(svc)):
    reg = await s.require_register(write=True)
    row = await s.db.get(WorkstreamDefinition, workstream_id)
    if row is None or row.register_id != reg.id:
        fail(404, "WORKSTREAM_NOT_FOUND", "Workstream not found")
    before = serialize(row)
    for k, v in data.model_dump(exclude_unset=True).items(): setattr(row, k, v)
    await s.bump(reg)
    s.audit(reg, "workstream", row.id, "updated", before=before, after=serialize(row))
    s.event(reg, "item.updated")
    return serialize(row)

@router.put(PREFIX + "/items/{item_id}/checkpoints/{workstream_id}", dependencies=[EDIT])
async def put_checkpoint(item_id: uuid.UUID, workstream_id: uuid.UUID, data: CheckpointWrite, s: RegisterService = Depends(svc)):
    reg = await s.require_register(write=True)
    item = await s.require_item(reg, item_id, write=True)
    workstream = await s.db.get(WorkstreamDefinition, workstream_id)
    if not workstream:
        fail(404, "WORKSTREAM_NOT_FOUND", "Workstream not found")
    return serialize(await s.put_checkpoint(reg, item, workstream, data))

@router.patch(PREFIX + "/checkpoints/bulk", dependencies=[EDIT])
async def bulk_checkpoint(data: CheckpointBulk, s: RegisterService = Depends(svc)):
    reg = await s.require_register(write=True)
    if len({(i.item_id, i.workstream_id) for i in data.updates}) != len(data.updates):
        fail(422, "DUPLICATE_CHECKPOINT", "Bulk contains duplicate item/workstream")
    result = []
    for update in data.updates:
        item = await s.require_item(reg, update.item_id, write=True)
        ws = await s.db.get(WorkstreamDefinition, update.workstream_id)
        if ws is None:
            fail(404, "WORKSTREAM_NOT_FOUND", "Workstream not found")
        result.append(serialize(await s.put_checkpoint(reg, item, ws, CheckpointWrite(**update.model_dump(exclude={"item_id", "workstream_id"})))))
    return {"items": result}

@router.get(PREFIX + "/items/{item_id}/references", dependencies=[READ])
async def references(item_id: uuid.UUID, s: RegisterService = Depends(svc)):
    reg = await s.require_register()
    item = await s.require_item(reg, item_id)
    return {"items": [serialize(x) for x in await s.repo.references(item.id)]}

@router.post(PREFIX + "/items/{item_id}/references", dependencies=[EDIT], status_code=201)
async def add_reference(item_id: uuid.UUID, data: ReferenceCreate, s: RegisterService = Depends(svc)):
    reg = await s.require_register(write=True)
    item = await s.require_item(reg, item_id, write=True)
    await s.validate_reference(data)
    if any(r.kind == data.kind and r.owner_id == data.owner_id and r.namespace == data.namespace and r.external_key == data.external_key for r in await s.repo.references(item.id)):
        fail(409, "DUPLICATE_REFERENCE", "Reference already linked")
    row = ItemReference(project_id=s.project_id, item_id=item.id, created_by=s.actor_id, **data.model_dump())
    s.db.add(row)
    await s.db.flush()
    await s.bump(reg)
    s.audit(reg, "reference", row.id, "created", after=serialize(row))
    s.event(reg, "reference.changed", item_id=item.id)
    return serialize(row)

@router.delete(PREFIX + "/items/{item_id}/references/{ref_id}", dependencies=[EDIT])
async def delete_reference(item_id: uuid.UUID, ref_id: uuid.UUID, s: RegisterService = Depends(svc)):
    reg = await s.require_register(write=True)
    await s.require_item(reg, item_id, write=True)
    row = await s.db.get(ItemReference, ref_id)
    if row is None or row.item_id != item_id or row.project_id != s.project_id:
        fail(404, "REFERENCE_NOT_FOUND", "Reference not found")
    old = serialize(row)
    await s.db.delete(row)
    await s.bump(reg)
    s.audit(reg, "reference", ref_id, "unlinked", before=old)
    s.event(reg, "reference.changed", item_id=item_id)
    return {"deleted": True}

@router.get(PREFIX + "/items/{item_id}/audit", dependencies=[READ])
async def audit(item_id: uuid.UUID, s: RegisterService = Depends(svc), page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    reg = await s.require_register()
    await s.require_item(reg, item_id)
    stmt = select(RegisterAudit).where(RegisterAudit.project_id == s.project_id, RegisterAudit.register_id == reg.id,
             RegisterAudit.entity_id == item_id)
    total = (await s.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    records = list((await s.db.execute(stmt.order_by(RegisterAudit.occurred_at.desc()).offset((page-1)*page_size).limit(page_size))).scalars())
    return {"page": page, "page_size": page_size, "total": total, "items": [serialize(x) for x in records]}

@router.get(PREFIX + "/summary", dependencies=[READ])
async def summary(s: RegisterService = Depends(svc)):
    return await s.summary(await s.require_register())

@router.post(PREFIX + "/import/preview", dependencies=[IMPORT])
async def preview_import(file: UploadFile = File(...), s: RegisterService = Depends(svc)):
    reg = await s.require_register()
    from .excel_io import preview
    content = await file.read(10 * 1024 * 1024 + 1)
    return await preview(s, reg, content, file.filename or "")

@router.post(PREFIX + "/import/commit", dependencies=[IMPORT])
async def commit_import(file: UploadFile = File(...), preview_sha256: str = Form(...),
                        expected_register_version: int = Form(...), resolutions: str = Form("{}"),
                        s: RegisterService = Depends(svc)):
    reg = await s.require_register(write=True)
    from .excel_io import commit
    content = await file.read(10 * 1024 * 1024 + 1)
    return await commit(s, reg, content, file.filename or "", preview_sha256, expected_register_version, resolutions)

@router.get(PREFIX + "/export", dependencies=[EXPORT])
async def export(format: str = Query(default="legacy", pattern="^(legacy|extended)$"), s: RegisterService = Depends(svc)):
    reg = await s.require_register()
    from .excel_io import export_xlsx
    content = await export_xlsx(s, reg, format)
    return StreamingResponse(BytesIO(content), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": 'attachment; filename="drawing-log.xlsx"'})
