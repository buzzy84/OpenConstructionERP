"""Production Drawing Register: eight additive, project-scoped tables.

Revision ID: v3325_production_register
Revises: v3324_buyer_selection_currency

Inspector guards are intentional: the application's bootstrap may have already
executed Base.metadata.create_all() before Alembic runs.
"""
from __future__ import annotations
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "v3325_production_register"
down_revision: Union[str, Sequence[str], None] = "v3324_buyer_selection_currency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GUID = sa.Uuid(as_uuid=True)


def pkcols():
    return [sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())]


def c(name, typ, *, nullable=True, default=None):
    return sa.Column(name, typ, nullable=nullable, server_default=default)


def project(*, fk=False):
    if fk:
        return sa.Column("project_id", GUID, sa.ForeignKey("oe_projects_project.id", ondelete="CASCADE"), nullable=False)
    return c("project_id", GUID, nullable=False)


def fkcolumn(name, table, *, ondelete="CASCADE"):
    return sa.Column(name, GUID, sa.ForeignKey(f"oe_production_register_{table}.id", ondelete=ondelete), nullable=False)


def schema():
    return [
        ("oe_production_register_register", [project(fk=True), c("contract_id", GUID, nullable=False), c("boq_id", GUID, nullable=False),
             c("baseline_snapshot_id", GUID, nullable=False), c("created_by", GUID),
             c("legacy_code_header", sa.String(120), nullable=False, default="INTERNAL ITEM CODE"),
             c("created_mode", sa.String(16), nullable=False, default="empty"), c("state", sa.String(16), nullable=False, default="active"),
             c("version", sa.Integer(), nullable=False, default="1"),
             sa.UniqueConstraint("project_id", name="uq_pr_register_project")]),
        ("oe_production_register_item", [fkcolumn("register_id", "register"), project(), c("display_order", sa.Integer(), nullable=False, default="0"),
             *[c(key, sa.String(length), nullable=False, default="") for key, length in (("floor",120),("room",160),("category",160),("item_code",160))],
             *[c(key, sa.Text(), nullable=False, default="") for key in ("description","specification","comments","change_notes","notes")],
             c("quoted_qty_raw",sa.String(120)), c("production_qty_raw",sa.String(120)), c("quoted_unit",sa.String(40)),
             c("production_unit",sa.String(40)), c("drafter_name",sa.String(255)), c("drafter_user_id",GUID),
             c("reported_approval_date",sa.Date()), c("scope",sa.String(24),nullable=False,default="ours"),
             c("lifecycle",sa.String(24),nullable=False,default="active"), c("origin",sa.String(24),nullable=False,default="manual"),
             c("version",sa.Integer(),nullable=False,default="1"), c("archived_at",sa.DateTime(timezone=True))]),
        ("oe_production_register_boq_link", [project(),fkcolumn("item_id","item"),c("boq_id",GUID,nullable=False),
             c("baseline_snapshot_id",GUID,nullable=False),c("boq_position_id",GUID),c("boq_ref_raw",sa.String(255),nullable=False),
             c("resolution",sa.String(16),nullable=False,default="unresolved"),c("sort_order",sa.Integer(),nullable=False,default="0"),
             sa.UniqueConstraint("item_id","boq_ref_raw",name="uq_pr_link_item_raw")]),
        ("oe_production_register_relation", [project(),fkcolumn("parent_item_id","item"),fkcolumn("child_item_id","item"),
             c("kind",sa.String(20),nullable=False,default="contains"),c("created_by",GUID),
             sa.UniqueConstraint("parent_item_id","child_item_id","kind",name="uq_pr_relation_pair")]),
        ("oe_production_register_workstream", [project(),fkcolumn("register_id","register"),
             c("code",sa.String(64),nullable=False),c("label",sa.String(160),nullable=False),
             c("category",sa.String(24),nullable=False,default="other"),c("sort_order",sa.Integer(),nullable=False,default="0"),
             c("legacy_column",sa.String(64)),c("enabled",sa.Boolean(),nullable=False,default=sa.text("true")),
             sa.UniqueConstraint("register_id","code",name="uq_pr_workstream_code")]),
        ("oe_production_register_checkpoint", [project(),fkcolumn("item_id","item"),fkcolumn("workstream_id","workstream",ondelete="RESTRICT"),
             c("status",sa.String(20),nullable=False,default="unknown"),c("reported_value",sa.Text()),
             c("planned_date",sa.Date()),c("actual_date",sa.Date()),c("assignee_name",sa.String(255)),
             c("assignee_user_id",GUID),c("notes",sa.Text(),nullable=False,default=""),
             c("source",sa.String(16),nullable=False,default="manual"),c("updated_by",GUID),
             c("version",sa.Integer(),nullable=False,default="1"),
             sa.UniqueConstraint("item_id","workstream_id",name="uq_pr_checkpoint_item_ws")]),
        ("oe_production_register_reference", [project(),fkcolumn("item_id","item"),c("kind",sa.String(32),nullable=False),
             c("owner_id",GUID),c("namespace",sa.String(100)),c("external_key",sa.String(255)),c("uri",sa.String(1000)),
             c("label",sa.String(255),nullable=False,default=""),c("created_by",GUID)]),
        ("oe_production_register_audit", [project(),c("register_id",GUID,nullable=False),
             c("entity_kind",sa.String(24),nullable=False),c("entity_id",GUID,nullable=False),c("action",sa.String(40),nullable=False),
             c("actor_id",GUID),c("source",sa.String(16),nullable=False,default="api"),
             c("before",sa.JSON(),nullable=False,default="{}"),c("after",sa.JSON(),nullable=False,default="{}"),
             c("reason",sa.Text()),c("occurred_at",sa.DateTime(timezone=True),nullable=False)]),
    ]

INDEXES = [
    ("ix_pr_register_project_id","oe_production_register_register",["project_id"]),
    ("ix_pr_item_project_register_order","oe_production_register_item",["project_id","register_id","display_order"]),
    ("ix_pr_item_project_code","oe_production_register_item",["project_id","item_code"]),
    ("ix_pr_boq_link_project_id","oe_production_register_boq_link",["project_id"]),
    ("ix_pr_boq_link_item_id","oe_production_register_boq_link",["item_id"]),
    ("ix_pr_audit_project_entity_at","oe_production_register_audit",["project_id","entity_id","occurred_at"]),
    ("ix_pr_audit_register_id","oe_production_register_audit",["register_id"]),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())
    for name, cols in schema():
        if name not in existing:
            op.create_table(name, *pkcols(), *cols)
    for index, table, cols in INDEXES:
        inspector = sa.inspect(bind)
        if not any(idx["name"] == index for idx in inspector.get_indexes(table)):
            op.create_index(index, table, cols)


def downgrade() -> None:
    bind = op.get_bind()
    for name, _cols in reversed(schema()):
        if sa.inspect(bind).has_table(name):
            op.drop_table(name)
