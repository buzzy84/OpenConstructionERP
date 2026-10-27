"""Production register: project-scoped operational mapping, never a BOM or drawing owner."""
from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Any
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base, GUID

class ProductionRegister(Base):
    __tablename__ = "oe_production_register_register"
    __table_args__ = (UniqueConstraint("project_id", name="uq_pr_register_project"),)
    project_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("oe_projects_project.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    boq_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    baseline_snapshot_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
    legacy_code_header: Mapped[str] = mapped_column(String(120), nullable=False, default="INTERNAL ITEM CODE")
    created_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="empty")
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

class ProductionItem(Base):
    __tablename__ = "oe_production_register_item"
    __table_args__ = (Index("ix_pr_item_project_register_order", "project_id", "register_id", "display_order"), Index("ix_pr_item_project_code", "project_id", "item_code"))
    register_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("oe_production_register_register.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    floor: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    room: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    category: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    item_code: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    specification: Mapped[str] = mapped_column(Text, nullable=False, default="")
    quoted_qty_raw: Mapped[str | None] = mapped_column(String(120))
    production_qty_raw: Mapped[str | None] = mapped_column(String(120))
    quoted_unit: Mapped[str | None] = mapped_column(String(40))
    production_unit: Mapped[str | None] = mapped_column(String(40))
    comments: Mapped[str] = mapped_column(Text, nullable=False, default="")
    change_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    drafter_name: Mapped[str | None] = mapped_column(String(255))
    drafter_user_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    reported_approval_date: Mapped[date | None] = mapped_column(Date())
    scope: Mapped[str] = mapped_column(String(24), nullable=False, default="ours")
    lifecycle: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    origin: Mapped[str] = mapped_column(String(24), nullable=False, default="manual")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class ItemBOQLink(Base):
    __tablename__ = "oe_production_register_boq_link"
    __table_args__ = (UniqueConstraint("item_id", "boq_ref_raw", name="uq_pr_link_item_raw"),)
    project_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("oe_production_register_item.id", ondelete="CASCADE"), nullable=False, index=True)
    boq_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    baseline_snapshot_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    boq_position_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    boq_ref_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    resolution: Mapped[str] = mapped_column(String(16), nullable=False, default="unresolved")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

class ItemRelation(Base):
    __tablename__ = "oe_production_register_relation"
    __table_args__ = (UniqueConstraint("parent_item_id", "child_item_id", "kind", name="uq_pr_relation_pair"),)
    project_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    parent_item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("oe_production_register_item.id", ondelete="CASCADE"), nullable=False)
    child_item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("oe_production_register_item.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="contains")
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID())

class WorkstreamDefinition(Base):
    __tablename__ = "oe_production_register_workstream"
    __table_args__ = (UniqueConstraint("register_id", "code", name="uq_pr_workstream_code"),)
    register_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("oe_production_register_register.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False, default="other")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    legacy_column: Mapped[str | None] = mapped_column(String(64))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class ItemCheckpoint(Base):
    __tablename__ = "oe_production_register_checkpoint"
    __table_args__ = (UniqueConstraint("item_id", "workstream_id", name="uq_pr_checkpoint_item_ws"),)
    project_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("oe_production_register_item.id", ondelete="CASCADE"), nullable=False)
    workstream_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("oe_production_register_workstream.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    reported_value: Mapped[str | None] = mapped_column(Text())
    planned_date: Mapped[date | None] = mapped_column(Date())
    actual_date: Mapped[date | None] = mapped_column(Date())
    assignee_name: Mapped[str | None] = mapped_column(String(255))
    assignee_user_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

class ItemReference(Base):
    __tablename__ = "oe_production_register_reference"
    project_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("oe_production_register_item.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    namespace: Mapped[str | None] = mapped_column(String(100))
    external_key: Mapped[str | None] = mapped_column(String(255))
    uri: Mapped[str | None] = mapped_column(String(1000))
    label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID())

class RegisterAudit(Base):
    __tablename__ = "oe_production_register_audit"
    __table_args__ = (Index("ix_pr_audit_project_entity_at", "project_id", "entity_id", "occurred_at"),)
    project_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    register_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    entity_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="api")
    before: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    after: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reason: Mapped[str | None] = mapped_column(Text())
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
