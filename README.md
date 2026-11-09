# AISYS RFID-Enabled Library Management System

Candidate technical evaluation - November 2026.

This repository contains a local working library-management prototype,
proposed production architecture, technical documentation, and
reproducible test evidence. All demonstration records are synthetic.

## Technology stack

- Frontend: React and TypeScript.
- Backend: Python FastAPI.
- Local persistence: SQLite, SQLAlchemy and Alembic.
- Production database proposal: PostgreSQL (not deployed).
- RFID: synthetic software-only EPC assignment, scan and security-state simulation.
- Integration: mock NCIP/SIP2 adapters and a transactional outbox.

## Project implementation summary

- Phase 1: requirements baseline - 12 FR, 9 NFR and 10 AC.
- Phase 2: architecture, data model, APIs, integrations and security design.
- Phase 3: working local prototype and initial automated test evidence.
- Phase 4: historical technical report, presentation and canonical RTM.
- Phase 5: CSV member import staging/reconciliation, loan renewal,
  fine-limit rules, mock NCIP/SIP2 adapters, transactional outbox
  and manually invoked dispatch/retry handling.
- Phase 6: simulated RFID security-state transitions and mock
  inventory reconciliation.
- Phase 7: updated report, 16-slide presentation, canonical RTM,
  evaluator demonstration guide and local verification evidence.

## Latest recorded verification - November 9, 2026

- Backend Pytest: 114 passed, zero failed, one deprecation warning.
- Frontend TypeScript/Vite production build: passed.
- SQLite integrity: OK, with zero foreign-key violations.
- Alembic database and script heads: 5c4d888ae5e1.
- Verification record: `evidence/phase7/final-verification.md`.

These checks do not constitute institutional acceptance or
production/hardware certification.

## Quick navigation

- [Final submission index](docs/final/README.md)
- [Final technical report (PDF)](docs/final/AISYS_Final_Technical_Report.pdf)
- [Final presentation](docs/final/AISYS_Final_Presentation_16_Slides.pptx)
- [Canonical requirements RTM](docs/final/AISYS_Final_Canonical_RTM.xlsx)
- [Evaluator demonstration guide](docs/final/AISYS_Evaluator_Demonstration_Guide.md)
- [Documentation index](docs/README.md)
- [Phase 3 historical runbook](docs/implementation/phase3-prototype-runbook.md)
- [Phase 5 implementation](docs/implementation/phase5-core-gap-closure.md)
- [Phase 6 implementation](docs/implementation/phase6-rfid-inventory-preview.md)

## Implementation boundaries

Physical RFID readers and gates, live institutional ILMS integration,
certified NCIP/SIP2 operation, persistent shelf stocktaking,
20,000-row spreadsheet acceptance, offline deployment and
production-level security/performance qualification remain incomplete.

The authoritative current coverage assessment is
`docs/final/AISYS_Final_Canonical_RTM.xlsx`.
No combined AC01-AC10 scenario is signed off as fully accepted.

Never commit credentials, .env files, authentication tokens,
local SQLite databases or real member information.

**Submission deadline:** November 10, 2026.
