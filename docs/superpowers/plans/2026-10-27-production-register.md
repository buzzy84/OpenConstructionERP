# Production Drawing Register Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one operational, project-scoped OCERP Drawing Log that links approved commercial BOQ references to production items and records manual checkpoints; no external connectors.

**Architecture:** `oe_production_register` optional backend module + opt-in frontend module. Existing OCERP owns BOQ, projects, contracts, drawings and approvals. The register stores only its own operational entities and read-only owner references; middleware may later call these ordinary REST APIs.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2, React 18, TS, React Query, openpyxl (existing dependency).

**Spec:** `OCERP_Drawing_Log_Superpowers_Implementation_Prompt_v3.md` (user-approved, not shipped with public code)

## Global Constraints

- Do not access PDM, MES, BC or orchestration engines from this module.
- No new foreign keys into optional modules; no BOQ writes.
- Immutable register contract, BOQ and baseline IDs.
- One register per project, immutable snapshot-based BOQ matching and many-to-many mapping.
- No hard delete of items or audit. Explicit project membership and permission checks on each route.
- Track unknown state without inventing completion or formal drawing approval.
- All UI strings localized; commit only synthetic fixtures.

## Review Focus

- Repeat code across multiple room/floors and even repeated within the same room: preserve distinct UUIDs.
- Concurrent PATCH/checkpoint writes: return 409 and preserve one winner.
- BOQ ordinal repeated in approved snapshot: mark ambiguous, never silently pick one.
- Two projects with identical codes: authorization and reference validation must reject foreign IDs.
- XLSX formulas and formula-like strings: reject input formula and ensure exported cells stay literal.

## Tasks

### Task 1 — Registration, schema and readiness

**Files:** `backend/app/modules/production_register/{manifest,models,schemas,repository,service,router,permissions,__init__}.py`, `backend/alembic/versions/v3325_production_register.py`.

- [ ] RED: assert module manifest registration, unique register/project, gate absence for default-active project.
- [ ] GREEN: implement 8 additive tables, permission gates and project/contract/BOQ snapshot eligibility.
- [ ] VERIFY: `pytest backend/tests/modules/test_production_register_unit.py`.

### Task 2 — Items, immutable BOQ mapping, relations and audit

- [ ] RED: repeated item codes, 4-to-1 BOQ links, shared refs, version conflict, cycles, cross-project IDOR.
- [ ] GREEN: CRUD and exact snapshot ordinal lookup, append-only audit, project-bound endpoints.
- [ ] VERIFY: focused tests and API OpenAPI generation.

### Task 3 — Workstreams and typed references

- [ ] RED: eight seed workstreams, unknown status, manual changes without connector, item/reference project-scoping.
- [ ] GREEN: configurable workstreams, checkpoints, bulk endpoint and typed OCERP links.
- [ ] VERIFY: focused tests including version races.

### Task 4 — Excel round-trip

- [ ] RED: 20 columns, embedded newline BOQ, grouping, duplicate codes, date/quantity literals, `_OCERP_SYNC`, corrupt file, formulas.
- [ ] GREEN: stateless preview/commit, export legacy+extended, hidden stable IDs, no formula execution.
- [ ] VERIFY: synthetic fixture only, export→import equivalence and idempotent retry.

### Task 5 — Native frontend module and project entry point

- [ ] RED: component tests for create without readiness, item grid, BOQ links, checkpoints, import conflicts, 404.
- [ ] GREEN: module registry, project shortcut, register page, item detail drawer, import wizard.
- [ ] VERIFY: `npm run lint && npm run build` inside the full OCERP checkout.

### Task 6 — Integration tests and migration guard

- [ ] RED: rollback/retry, audit + post-commit event only, no cross-system outbound transport.
- [ ] GREEN: harden module and migration, address findings.
- [ ] VERIFY: `cd backend && ruff format --check . && ruff check . && pytest`, `cd frontend && npm run build`; root `scripts/check_*.py` applicable guards; logs must be retained.

### Task 7 — Final review and delivery

- [ ] Run clean-worktree overlay script, review diff and integration, check no vendor connector code.
- [ ] Deliver a reusable local patch/ZIP and a report separating verified results from environment-specific unverified gates.
- [ ] Do not open an upstream PR; upstream explicitly does not merge external PRs.
