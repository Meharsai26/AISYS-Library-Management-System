# Phase 6 — RFID Security-State and Mock Inventory Preview

## 1. Scope

Phase 6 extends the AISYS RFID-Enabled Library Management
System demonstration prototype.

The implementation uses synthetic RFID EPC identifiers,
a FastAPI backend, SQLAlchemy and SQLite.

No physical RFID hardware, institutional library system
or production device infrastructure was connected.

## 2. Implemented — RFID Security-State Simulation

Existing circulation APIs were extended:

- POST /api/v1/loans/checkout
- POST /api/v1/loans/{loan_id}/return

Successful checkout updates the associated ACTIVE RFID
tag's security_armed field to false.

Successful return updates the associated ACTIVE RFID
tag's security_armed field to true.

The RFID database update occurs within the same
SQLAlchemy transaction as the relevant circulation
changes, audit event and mock ILMS integration outbox.

Items without associated RFID tags remain supported.

This is a local database simulation of RFID security
state, not a physical device command or acknowledgement.

## 3. Implemented — Mock Inventory Preview

Endpoint:

POST /api/v1/inventory/reconcile/mock

Authorization:

Requires tag:read permission.

Request example:

    {
      "scanned_epcs": [
        "MOCK-EPC-001",
        "MOCK-EPC-UNKNOWN"
      ]
    }

The endpoint compares synthetic scanned EPC values
against currently registered ACTIVE RFID tags.

Available items determine the expected on-shelf set.

Response categories:

- matched_epcs:
  ACTIVE registered tags expected and observed.

- missing_epcs:
  ACTIVE registered tags expected but not observed.

- unexpected_known_epcs:
  ACTIVE registered tags observed but associated with
  items not currently AVAILABLE.

- unknown_epcs:
  Observed EPCs without an ACTIVE tag association.

Duplicate EPC reads are deduplicated.

The response also includes summary counts and flags
indicating mock operation and lack of persistent sessions.

No inventory database records are created.

## 4. Automated Verification

Phase 5 baseline:

101 backend tests passed.

Phase 6 additions:

- 4 RFID security-state integration tests.
- 9 mock inventory preview tests.

Final Phase 6 backend regression:

114 passed, 1 nonblocking Starlette/httpx
deprecation warning.

Pytest exit code: 0.

Tests use isolated in-memory SQLite databases
and synthetic authentication identities.

## 5. Requirements Traceability

RFID security-state simulation:

Partially demonstrates desired security-state behavior
during checkout and return.

It does not implement physical tag programming,
device acknowledgements or the proposed
tag_security_sync model.

Inventory preview:

Partially demonstrates RFID scan reconciliation.

It does not fully satisfy AC05 because persistent
inventory sessions, expected-item snapshots,
shelf assignments, misplaced-item detection and
finalized reproducible reconciliation are absent.

AC06 gate and offline incident workflows:

Not implemented.

## 6. Explicit Limitations

The following remain outside verified implementation:

- Physical RFID readers and security-bit writing.
- Hardware acknowledgement and synchronization.
- Standards-compliant NCIP/SIP2 communication.
- Persistent inventory sessions.
- Immutable expected-item snapshots.
- Shelf-level misplaced-item detection.
- Gate-event ingestion and alarm processing.
- Offline buffering and replay.
- Camera, email, printer and notification integration.
- Production infrastructure and institutional UAT.

The inventory preview uses current database state,
which can change between calls.

It must not be presented as a finalized physical
stocktake or an institutional inventory audit.

## 7. Implementation Files

Modified:

- backend/app/api/circulation.py
- backend/app/main.py

Added:

- backend/app/api/inventory.py
- backend/tests/test_rfid_security_state.py
- backend/tests/test_inventory_preview.py

## 8. Phase 7 Follow-up

Before AISYS submission:

1. Reconcile technical report with Phases 5 and 6.
2. Update the 16-slide presentation.
3. Reconcile the canonical requirements traceability matrix.
4. Verify frontend build, database integrity and migrations.
5. Prepare a repeatable synthetic demonstration.
6. Validate final GitHub links and submission files.
7. Clearly distinguish implemented, mocked, proposed
   and deferred capabilities.
