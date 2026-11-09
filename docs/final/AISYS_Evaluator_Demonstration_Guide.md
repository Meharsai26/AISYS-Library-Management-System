# AISYS RFID-Enabled Library Management System
## Evaluator Demonstration and Local Execution Guide

**Technical evaluation:** November 2026  
**Implementation:** Local working prototype with simulated RFID and ILMS boundaries  
**Production status:** Not production certified

---

## 1. Purpose and scope

This guide provides reproducible steps for demonstrating the implemented
AISYS Library Management System prototype.

The prototype uses:
- React and TypeScript for the frontend.
- Python FastAPI for the backend.
- SQLAlchemy, Alembic and SQLite for local data persistence.
- Software-only synthetic RFID adapters.
- Mock NCIP/SIP2 adapters and a transactional integration outbox.

Use synthetic library records only.

No physical RFID reader, gate, smart-card device or institutional ILMS
is connected.

## 2. Prerequisites

- Windows PowerShell.
- Python 3.13.
- Node.js and npm.
- Git.
- Repository checked out locally.

The recorded Phase 7 verification used Python 3.13.1 and Node.js 22.14.0.

## 3. Backend setup

Open PowerShell from the repository root.

```powershell
Set-Location .\backend

py -3.13 -m venv .venv

.\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}

.\.venv\Scripts\python.exe -m alembic upgrade head

.\.venv\Scripts\python.exe -m scripts.seed_auth

.\.venv\Scripts\python.exe -m scripts.seed_library

.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The authentication seed prompts for demonstration passwords.
Never include those passwords in repository commits, reports or screenshots.

Backend API documentation:

http://127.0.0.1:8000/docs

If the environment has already been initialized, avoid recreating or
reseeding it unnecessarily.

## 4. Frontend setup

Open a second PowerShell window from the repository root.

```powershell
Set-Location .\frontend

npm ci

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}

npm run build

npm run dev
```

Open:

http://localhost:5173

The backend must be running for API-connected frontend actions.

## 5. Authentication demonstration

Use the synthetic administrator created by the authentication seed.

1. Open the React application.
2. Log in using the locally created demonstration credentials.
3. Confirm that the authenticated staff interface loads.
4. Open Swagger to inspect protected API endpoints.
5. Demonstrate access to authorized actions.

Relevant API routes:

- POST /api/v1/auth/login
- GET /api/v1/auth/me
- POST /api/v1/auth/logout

The backend enforces role/permission checks on protected routes.

## 6. Catalog and circulation demonstration

Use unique synthetic identifiers for new records.

1. Create a bibliographic record.
2. Create a physical item linked to the record.
3. Create a synthetic library member.
4. Check out an available item.
5. Record the resulting loan ID.
6. Verify the item's checked-out state.
7. Renew the loan where policy permits.
8. Return the loan by loan ID.
9. Verify the item's available state.

Relevant API routes:

- GET /api/v1/bibliographic-records
- POST /api/v1/bibliographic-records
- GET /api/v1/items
- POST /api/v1/items
- GET /api/v1/members
- POST /api/v1/members
- POST /api/v1/loans/checkout
- POST /api/v1/loans/{loan_id}/renew
- POST /api/v1/loans/{loan_id}/return

The backend includes selected renewal, eligibility and fine-limit rules.

Use Swagger's generated request schemas for payload fields.
Do not assume that all backend functionality has a dedicated React screen.

## 7. Synthetic RFID demonstration

Use an existing physical item ID.

1. Open Swagger and authorize with an appropriate demo account.
2. Call POST /api/v1/rfid/tags/assign.
3. Associate a unique synthetic EPC with the item.
4. Call POST /api/v1/rfid/scans/mock.
5. Verify that the EPC resolves to the expected item.
6. Review the simulated RFID security state during checkout/return.

Relevant API routes:

- POST /api/v1/rfid/tags/assign
- POST /api/v1/rfid/scans/mock

The mock scan explicitly does not represent a connected physical reader.

Checkout/return security-state behavior is simulated in software.
There is no physical RFID tag write or reader acknowledgement.

## 8. Mock inventory demonstration

Relevant API route:

- POST /api/v1/inventory/reconcile/mock

Use Swagger to inspect its request schema.

The mock inventory reconciliation can classify:

- Expected and observed tags that match.
- Expected tags missing from the observed scan.
- Unexpected tags belonging to known items.
- Unknown EPC values.

Repeated EPC scans are deduplicated in the mock comparison.

This is a preview API, not a persistent physical shelf-stocktaking
workflow. Audible confirmation, real readers and complete misplaced-item
identification are not delivered.

## 9. CSV member migration demonstration

Relevant API route:

- POST /api/v1/imports/members

Use a small synthetic UTF-8 CSV file.

Demonstrate the supported staging, input validation, duplicate handling,
reconciliation and transactional rollback behavior.

Inspect the Swagger request definition before uploading.

Do not use institutional or personal member data.

The prototype does not demonstrate native XLSX ingestion or the full
20,000-record spreadsheet acceptance requirement.

## 10. Mock institutional integration

The backend contains NCIP/SIP2 mock adapters and a transactional
circulation-event outbox.

The mock dispatch mechanism is manually invoked within the prototype's
test/integration workflow; it is not an automatic production worker.

Demonstrate its behavior through the documented implementation tests
and recorded evidence.

Do not claim a live NCIP/SIP2 exchange or connected institutional ILMS.

## 11. Reproduce automated verification

In the backend directory:

```powershell
.\.venv\Scripts\python.exe -m pytest -q

.\.venv\Scripts\python.exe -m alembic current
```

In the frontend directory:

```powershell
npm run build
```

Recorded Phase 7 results:

- 114 backend tests passed.
- Zero backend test failures.
- One nonblocking Starlette deprecation warning.
- Frontend production build succeeded.
- SQLite integrity check returned `ok`.
- Foreign-key violation count was zero.
- Database and Alembic script heads matched at `5c4d888ae5e1`.

The verification record is:

`evidence/phase7/final-verification.md`

These results are local development-environment verification, not
institutional user acceptance or hardware qualification.

## 12. Evaluator walkthrough sequence

Recommended demonstration order:

1. Explain the system architecture and technology stack.
2. Start backend and frontend.
3. Log in using synthetic credentials.
4. Show catalog and physical-copy creation.
5. Register a synthetic member.
6. Demonstrate checkout, renewal and return.
7. Show synthetic RFID tag assignment and scan.
8. Explain security-state simulation.
9. Show mock inventory reconciliation.
10. Demonstrate synthetic CSV member import.
11. Present mock integration and outbox test evidence.
12. Show the 114-test verification result.
13. Review the RTM and explicitly identify the incomplete requirements.

## 13. Documentation and evidence

Final submission artifacts:

- `docs/final/AISYS_Final_Technical_Report.docx`
- `docs/final/AISYS_Final_Technical_Report.pdf`
- `docs/final/AISYS_Final_Presentation_16_Slides.pptx`
- `docs/final/AISYS_Final_Canonical_RTM.xlsx`
- This evaluator demonstration guide.

Additional implementation records:

- `docs/implementation/phase3-prototype-runbook.md`
- `docs/implementation/phase5-core-gap-closure.md`
- `docs/implementation/phase6-rfid-inventory-preview.md`
- `evidence/phase7/final-verification.md`

## 14. Important limitations

The following remain incomplete or unverified:

- Physical RFID device operation and gate alarms.
- Live NCIP/SIP2 and institutional ILMS integration.
- Production smart-card authentication.
- Persistent physical inventory sessions.
- Full 20,000-row spreadsheet acceptance demonstration.
- Automated integration dispatch workers.
- Offline installation, update and rollback validation.
- Production-grade deployment, security and performance testing.
- Full institutional acceptance of AC01-AC10.

The submitted prototype demonstrates an implemented software subset,
supported by local automated tests and documented design boundaries.

## 15. Data safety

Use synthetic records only.

Never commit or distribute:

- `.env` files containing local configuration or secrets.
- Passwords, session tokens or authorization headers.
- Local SQLite database files containing demonstration state.
- Virtual environments or Node.js dependencies.
- Real institutional or personal library-member records.
