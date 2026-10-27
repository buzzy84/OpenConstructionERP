"""Synthetic, deterministic tests for the project Drawing Log (never use customer data)."""
from datetime import date
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import HTTPException
from openpyxl import Workbook, load_workbook
from pydantic import ValidationError

from app.modules.production_register.excel_io import COLUMN_HEADERS, _boq_refs, _write_text, parse_xlsx
from app.modules.production_register.manifest import manifest
from app.modules.production_register.models import (
    ProductionRegister, ProductionItem, ItemBOQLink, ItemRelation, WorkstreamDefinition,
    ItemCheckpoint, ItemReference, RegisterAudit,
)
from app.modules.production_register.schemas import ItemInput, ItemPatch, CheckpointWrite, ReferenceCreate
from app.modules.production_register.service import INITIAL_WORKSTREAMS, RegisterService


def sample_workbook(*, formulas=False):
    book = Workbook()
    sheet = book.active
    sheet.title = 'Foglio1'
    sheet['A1'] = 'Synthetic drawing log'
    for index, h in enumerate(COLUMN_HEADERS, start=1):
        sheet.cell(3, index, h)
    sheet['A4'] = 'BASEMENT FLOOR'
    sheet['A5'] = 'WALL FINISHES'
    sheet['A6'] = 'ROOM-01'
    sheet['B6'] = 'A-001\nB-002;C-003'
    sheet['C6'] = 'UNIT-1+UNIT-2'
    sheet['D6'] = 'Display wall'
    sheet['F6'] = 'a corpo'
    sheet['G6'] = '4ml'
    sheet['K6'] = date(2026,8,25)
    sheet['L6'] = 'Supplier pending'
    sheet['A7'] = 'ROOM-02'
    sheet['B7'] = 'A-001'
    sheet['C7'] = 'UNIT-1+UNIT-2'
    sheet['D7'] = 'Second distinct occurrence'
    sheet['A8'] = 'ROOM-02'
    sheet['C8'] = 'UNIT-1+UNIT-2'
    sheet['D8'] = 'Third distinct occurrence'
    if formulas:
        sheet['D8'] = '=1+1'
    data=BytesIO();book.save(data)
    return data.getvalue()


def test_manifest_and_schema_expose_distinct_eight_tables():
    assert manifest.name == 'oe_production_register'
    assert manifest.category == 'community'
    classes = (ProductionRegister,ProductionItem,ItemBOQLink,ItemRelation,WorkstreamDefinition,
               ItemCheckpoint,ItemReference,RegisterAudit)
    assert len({x.__tablename__ for x in classes}) == 8
    assert all(x.__tablename__.startswith('oe_production_register_') for x in classes)
    assert 'item_code' not in [col.name for c in ProductionItem.__table__.constraints if hasattr(c,'columns') and c.__class__.__name__=='UniqueConstraint' for col in c.columns]
    assert len(INITIAL_WORKSTREAMS) == 8
    assert {x[0] for x in INITIAL_WORKSTREAMS} >= {'shipment_1','shipment_2','production','glass'}


def test_excel_keeps_many_boq_references_and_duplicate_item_codes():
    parsed = parse_xlsx(sample_workbook(), 'synthetic.xlsx')
    assert len(parsed['rows']) == 3
    a,b,c = parsed['rows']
    assert a['floor'] == 'BASEMENT FLOOR'
    assert a['category'] == 'WALL FINISHES'
    assert a['boq_refs'] == ['A-001','B-002','C-003']
    assert b['boq_refs'] == ['A-001']
    assert a['item_code'] == b['item_code'] == c['item_code'] == 'UNIT-1+UNIT-2'
    assert a['quoted_qty_raw'] == 'a corpo'
    assert a['production_qty_raw'] == '4ml'
    assert a['checkpoint_raw']['production'] == 'Supplier pending'
    assert a['reported_approval_date'] == '2026-08-25'


def test_excel_formula_refusal_and_magic_bytes():
    with pytest.raises(HTTPException) as exc:
        parse_xlsx(sample_workbook(formulas=True), 'example.xlsx')
    assert exc.value.status_code == 422
    with pytest.raises(HTTPException):
        parse_xlsx(b'not a zip', 'example.xlsx')
    with pytest.raises(HTTPException):
        parse_xlsx(sample_workbook(), 'example.xlsm')


def test_xlsx_formula_like_strings_are_text_not_formulas():
    book=Workbook(); ws=book.active
    tokens=['=1+1','+1+2','-1','@LOOKUP','UNIT-1+UNIT-2']
    for i,text in enumerate(tokens,1):
        _write_text(ws.cell(i,1),text)
    stream=BytesIO();book.save(stream);stream.seek(0)
    loaded=load_workbook(stream)
    for i,expected in enumerate(tokens,1):
        cell=loaded.active.cell(i,1)
        assert cell.value == expected
        assert cell.data_type != 'f'


def test_schema_does_not_accept_cross_project_or_audit_spoofing():
    with pytest.raises(ValidationError):
        ItemInput(item_code='X-1',project_id=str(uuid4()))
    with pytest.raises(ValidationError):
        ItemInput(item_code='X-1',source='api',created_by=str(uuid4()))
    with pytest.raises(ValidationError):
        ItemPatch(expected_version=0)
    with pytest.raises(ValidationError):
        CheckpointWrite(expected_version=0,status='approved')
    with pytest.raises(ValidationError):
        ReferenceCreate(kind='external',namespace='source',external_key=None)


def test_boq_ref_split_only_on_newline_semicolon():
    assert _boq_refs('CLN1+C14\nGRP_A-02; CLD-03') == ['CLN1+C14','GRP_A-02','CLD-03']


def test_optimistic_check_rejects_stale_clients():
    with pytest.raises(HTTPException) as exc:
        RegisterService.check_version(8,7)
    assert exc.value.status_code == 409
    RegisterService.check_version(8,8)
