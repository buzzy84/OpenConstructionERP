"""Typed contract for OCERP internal clients and external middleware callers."""
from __future__ import annotations
from datetime import date
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

class RegisterCreate(Strict):
    contract_id: UUID
    boq_id: UUID
    mode: Literal["empty", "from_boq", "excel"] = "empty"

class BOQLinkInput(Strict):
    boq_ref_raw: str = Field(min_length=1, max_length=255)
    boq_position_id: UUID | None = None

class ItemInput(Strict):
    item_code: str = Field(default="", max_length=160)
    floor: str = Field(default="", max_length=120)
    room: str = Field(default="", max_length=160)
    category: str = Field(default="", max_length=160)
    description: str = ""
    specification: str = ""
    quoted_qty_raw: str | None = Field(default=None, max_length=120)
    production_qty_raw: str | None = Field(default=None, max_length=120)
    quoted_unit: str | None = Field(default=None, max_length=40)
    production_unit: str | None = Field(default=None, max_length=40)
    comments: str = ""
    change_notes: str = ""
    notes: str = ""
    drafter_name: str | None = None
    drafter_user_id: UUID | None = None
    reported_approval_date: date | None = None
    scope: Literal["ours", "subcontracted", "by_others", "unknown"] = "ours"
    display_order: int = Field(default=0, ge=0)
    boq_links: list[BOQLinkInput] = Field(default_factory=list)

class ItemPatch(Strict):
    expected_version: int = Field(ge=1)
    item_code: str | None = Field(default=None, max_length=160)
    floor: str | None = Field(default=None, max_length=120)
    room: str | None = Field(default=None, max_length=160)
    category: str | None = Field(default=None, max_length=160)
    description: str | None = None
    specification: str | None = None
    quoted_qty_raw: str | None = None
    production_qty_raw: str | None = None
    comments: str | None = None
    change_notes: str | None = None
    notes: str | None = None
    drafter_name: str | None = None
    reported_approval_date: date | None = None
    scope: Literal["ours", "subcontracted", "by_others", "unknown"] | None = None

class Versioned(Strict):
    expected_version: int = Field(ge=1)

class ArchiveRequest(Versioned):
    reason: str = Field(min_length=3)

class BOQLinksReplace(Versioned):
    links: list[BOQLinkInput]

class RelationInput(Strict):
    child_item_id: UUID
    kind: Literal["contains", "depends_on", "replaces"] = "contains"

class RelationsReplace(Versioned):
    relations: list[RelationInput]

class WorkstreamCreate(Strict):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    label: str = Field(min_length=1, max_length=160)
    category: Literal["design", "production", "external", "shipping", "other"] = "other"
    sort_order: int = 100

class WorkstreamPatch(Strict):
    label: str | None = None
    sort_order: int | None = None
    enabled: bool | None = None

class CheckpointWrite(Strict):
    expected_version: int = Field(ge=0)
    status: Literal["unknown", "not_started", "in_progress", "on_hold", "completed", "not_applicable"] = "unknown"
    reported_value: str | None = None
    planned_date: date | None = None
    actual_date: date | None = None
    assignee_name: str | None = None
    assignee_user_id: UUID | None = None
    notes: str = ""

class CheckpointBulkItem(CheckpointWrite):
    item_id: UUID
    workstream_id: UUID

class CheckpointBulk(Strict):
    updates: list[CheckpointBulkItem] = Field(min_length=1, max_length=200)

class ReferenceCreate(Strict):
    kind: Literal["cde_container", "design_deliverable", "submittal", "change_order", "variation_request", "schedule_activity", "external"]
    owner_id: UUID | None = None
    namespace: str | None = None
    external_key: str | None = None
    uri: str | None = None
    label: str = ""

    @model_validator(mode="after")
    def validate_reference(self):
        if self.kind == "external":
            if not self.namespace or not self.external_key or self.owner_id:
                raise ValueError("external references require namespace and external_key, and no owner_id")
        elif not self.owner_id or self.namespace or self.external_key or self.uri:
            raise ValueError("OCERP references require owner_id without external fields")
        return self
