# AISYS RFID-Enabled Library Management System

Candidate technical evaluation — local prototype and proposed modular RFID-enabled library solution. All demonstration records are synthetic.

## Stack
- Frontend: React / TypeScript
- Backend: Python FastAPI
- Local demo database: SQLite / SQLAlchemy / Alembic
- Production target (design only): PostgreSQL
- RFID: software-only mock EPC tag assign/scan APIs

## Project status (2026-11-09)
- Phase 1: completed requirements baseline (12 FR, 9 NFR, 10 AC).
- Phase 2: completed proposed architecture and design; not an AISYS/vendor signoff.
- Phase 3: local prototype built; recorded evidence shows 19 backend tests passed and React production build succeeded. Browser-originated API flow and mock RFID assignment/scan verified.
- Phase 4: final technical report, presentation and canonical RTM in `docs/final/`.

## Navigation
- [Documentation index](docs/README.md)
- [Phase 3 runbook](docs/implementation/phase3-prototype-runbook.md)
- [Final submission](docs/final/README.md)

## Boundaries
No physical RFID, real institutional ILMS, operational NCIP/SIP2 integration, offline synchronization, or production deployment. Do not interpret proposal diagrams as verified implementations. The requirements and acceptance gap register is `docs/final/AISYS_Phase4_Canonical_RTM.xlsx`. No secrets, real user records, `.env` or SQLite files belong in version control.

**Submission deadline:** 10 November 2026.
