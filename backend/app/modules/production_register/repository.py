"""Queries only; transaction ownership lives in FastAPI's SessionDep."""
from __future__ import annotations
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import ProductionRegister, ProductionItem, ItemBOQLink, ItemCheckpoint, WorkstreamDefinition, ItemReference, ItemRelation, RegisterAudit

class ProductionRegisterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, project_id: UUID, *, for_update: bool = False):
        stmt = select(ProductionRegister).where(ProductionRegister.project_id == project_id)
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def item(self, register_id: UUID, project_id: UUID, item_id: UUID):
        return (await self.session.execute(select(ProductionItem).where(ProductionItem.id == item_id, ProductionItem.register_id == register_id, ProductionItem.project_id == project_id))).scalar_one_or_none()

    async def links(self, item_id: UUID):
        return list((await self.session.execute(select(ItemBOQLink).where(ItemBOQLink.item_id == item_id).order_by(ItemBOQLink.sort_order))).scalars())

    async def checkpoints(self, item_id: UUID):
        return list((await self.session.execute(select(ItemCheckpoint).where(ItemCheckpoint.item_id == item_id))).scalars())

    async def workstreams(self, register_id: UUID):
        return list((await self.session.execute(select(WorkstreamDefinition).where(WorkstreamDefinition.register_id == register_id).order_by(WorkstreamDefinition.sort_order))).scalars())

    async def references(self, item_id: UUID):
        return list((await self.session.execute(select(ItemReference).where(ItemReference.item_id == item_id))).scalars())

    async def relations(self, item_id: UUID):
        return list((await self.session.execute(select(ItemRelation).where(ItemRelation.parent_item_id == item_id))).scalars())
