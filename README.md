# AISYS RFID-Enabled Library Management System

Technical evaluation project for designing and demonstrating
a modular RFID-enabled library management solution.

## Project Overview
The system is designed to support cataloguing, circulation,
RFID tagging, inventory, migration, security, reporting,
and offline library operations.

All evaluation data is synthetic. Real RFID hardware and
existing institutional ILMS connections are not used.

## Technology Stack
- Frontend: React + TypeScript
- Backend: Python FastAPI
- Prototype database: SQLite
- Production database design: PostgreSQL
- RFID middleware: Python mock adapters
- Data migration: Python + Pandas
- Testing: Pytest

## Architecture
Layered modular monolith with dedicated application,
data, RFID middleware, interoperability, integration,
user-interface and operations boundaries.

See [System Architecture](docs/architecture/system-architecture.md).

## Documentation
Start with the [Documentation Index](docs/README.md).

Key design documents:
- [Database Design](docs/database/data-model.md)
- [REST API Contracts](docs/api/rest-api-contracts.md)
- [RFID Integrations](docs/integrations/integration-design.md)
- [Security and Business Rules](docs/security/security-and-business-rules.md)
- [Design Review](docs/decisions/design-review.md)

## Current Status
Phase 1: Requirements baseline completed.
Phase 2: Internal design review recorded; actions and Git verification pending.
Phase 3: Application implementation not started.

## Limitations
This is a candidate technical evaluation, not a certified
production system. External integrations use proposed mock
contracts, and no hardware or protocol certification is claimed.

## Submission
Prepared for the AISYS technical evaluation.
Deadline: November 10, 2026.
