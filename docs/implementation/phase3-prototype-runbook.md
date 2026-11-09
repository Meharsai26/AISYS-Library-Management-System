# Phase 3 - Prototype Setup and Demonstration

## Scope

This repository contains a local synthetic demonstration of the
AISYS RFID-Enabled Library Management System.

Implemented:
- React and TypeScript frontend
- Python FastAPI backend
- SQLite persistence with SQLAlchemy and Alembic
- Authentication and role-based authorization
- Catalog, physical items, and member management
- Checkout and return
- Software-only mock RFID tag assignment and scan

No physical RFID hardware or institutional ILMS is connected.

## Prerequisites

- Windows PowerShell
- Python 3.13
- Node.js and npm
- Git

## Backend setup

From the repository root:

1. cd backend
2. py -3.13 -m venv .venv
3. .\.venv\Scripts\python.exe -m pip install -r requirements.txt
4. Copy-Item .env.example .env
5. .\.venv\Scripts\python.exe -m alembic upgrade head
6. .\.venv\Scripts\python.exe -m scripts.seed_auth
7. .\.venv\Scripts\python.exe -m scripts.seed_library
8. .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

The authentication seed prompts for demonstration passwords.
Passwords must not be committed or included in evidence.

Backend Swagger: http://127.0.0.1:8000/docs

## Frontend setup

Open a separate PowerShell window:

1. cd frontend
2. npm ci
3. Copy-Item .env.example .env
4. npm run build
5. npm run dev

Frontend: http://localhost:5173

## Demonstration walkthrough

Use a synthetic ADMIN account.

1. Log in.
2. Add a bibliographic record.
3. Add a physical copy with a unique accession number.
4. Register a synthetic member.
5. Check out the copy to the member.
6. Verify the item is CHECKED_OUT.
7. Return the loan using its loan ID.
8. Verify the item is AVAILABLE.

## Mock RFID demonstration

The mock RFID endpoints are available in Swagger:

POST /api/v1/rfid/tags/assign
POST /api/v1/rfid/scans/mock

Authorize using a demo account with the required permissions.

Assign a unique synthetic EPC such as MOCK-EPC-DEMO001 to
an existing physical item ID, then scan the EPC.

The scan returns the matching item and reports
hardware_connected=false.

RFID functionality is API-only in the current prototype.
There is no frontend RFID workflow or physical reader.

## Verification

From backend:

.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -m pip check

From frontend:

npm run build

Recorded verification outputs are in evidence/phase3.

## Prototype limitations

- SQLite is for the local prototype; PostgreSQL is design-only.
- NCIP/SIP2 integrations are design-only.
- The RFID reader is software-only.
- Checkout and return do not synchronize RFID security state.
- No persistent request idempotency or durable outbox.
- No real payment, production gate, or hardware integration.
- Audit immutability, shared rate limiting and load testing are
  not implemented.
- Complete Phase 2 requirements are not implemented.

## Data safety

Use synthetic records only. Never commit .env, local SQLite
databases, authentication tokens, passwords or .venv folders.
