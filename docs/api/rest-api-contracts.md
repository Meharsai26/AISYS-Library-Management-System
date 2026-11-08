# REST API Catalogue & Contracts v0.1 — PROPOSED
Base URL `/api/v1`; content type `application/json`; UUID identifiers; UTC ISO timestamps. Protected calls require authenticated session/bearer token as configured, server-side permissions and correlation ID. Mutation calls accept `Idempotency-Key` where indicated. `GET` list endpoints paginate with `limit` (1..100), `cursor`; stable order. Never expose credentials, internal exception trace or full member contact details.

## Endpoints, permission and purpose
| Method | Path | Permission | Purpose |
|---|---|---|---|
| POST | /auth/login | public | authenticate demo user, rate limit |
| POST | /auth/logout | authenticated | revoke session |
| GET | /auth/me | authenticated | current user and permissions |
| GET,POST | /bibliographic-records | catalog:read, catalog:write | search/create title |
| GET,PATCH | /bibliographic-records/{id} | catalog:read, catalog:write | read/edit title |
| GET,POST | /items | catalog:read, catalog:write | list/add copy and accession |
| GET,PATCH | /items/{id} | catalog:read, catalog:write | read/update copy |
| GET,POST | /members | member:read, member:write | list/create member |
| GET,PATCH | /members/{id} | member:read, member:write | read/update status |
| POST | /rfid/tags/assign | tag:write | validate+assign tag |
| POST | /rfid/tags/retag | tag:write | audited retag |
| GET | /rfid/tags/{epc} | tag:read | resolve tag to item |
| POST | /loans/checkout | circulation:write | atomic checkout |
| POST | /loans/{id}/renew | circulation:write | extend due date |
| POST | /loans/{id}/return | circulation:write | atomic return |
| GET | /members/{id}/loans | member:read or self | loan history |
| GET | /members/{id}/fines | fine:read or self | balances |
| POST | /inventory/sessions | inventory:write | begin shelf scan |
| POST | /inventory/sessions/{id}/scans | inventory:write | bulk scan EPCs |
| POST | /inventory/sessions/{id}/finalize | inventory:write | finalize expected vs observed inventory |
| GET | /inventory/sessions/{id}/reconciliation | inventory:read | finalized missing/misplaced results |
| POST | /rfid/gate-events | device:ingest | idempotent gate event |
| GET | /gate-events | gate:read | incident log |
| GET | /reports/summary | report:read | filtered aggregates |
| GET,PATCH | /notification-preferences/{member_id} | self/admin | configure channels |
| GET,POST | /admin/users | admin:users | manage users |
| GET,POST | /admin/roles | admin:roles | manage roles |
| GET | /admin/audit-events | audit:read | restricted audit search |
| POST | /migration/batches | migration:write | upload synthetic spreadsheet |
| POST | /migration/batches/{id}/validate | migration:write | validate, dedup |
| POST | /migration/batches/{id}/dry-run | migration:write | preview results |
| POST | /migration/batches/{id}/commit | migration:commit | transactional import |
| GET | /migration/batches/{id}/reconciliation | migration:read | counts and errors |
| GET | /health/live | operational | liveness |
| GET | /health/ready | operational | readiness (restricted detail) |
| GET | /system/version | admin:read | installed version |

The endpoint catalogue expresses full design scope, NOT promised implementation scope. Gate ingest is device-authenticated, not public. Sensitive mutation calls require CSRF mitigation when using browser cookies; short-lived bearer tokens if using token auth.

## Method-level permissions and idempotency

Combined GET/POST and GET/PATCH catalogue entries represent
separate operations with separate authorization checks.

- GET requires the resource's read permission.
- POST and PATCH require the resource's write permission.
- Patron self-service requires resource ownership checks.
- Administrative endpoints require explicit admin permissions.
- Device ingestion requires authenticated device identity.

Idempotency-Key is mandatory for:
- Checkout, renewal and return.
- RFID tag assignment and retagging.
- Migration batch commit.

Identical retries return the previously committed response.
Key reuse with a different payload returns HTTP 409.
Persist the idempotency result atomically with the
corresponding business transaction.

Gate events use source_event_id for deduplication.

Inventory finalization uses a stable session ID and
returns the existing finalized result on identical retries.

Local circulation commits must be distinguished from
external RFID/ILMS synchronization status.
## Example contracts
### POST /api/v1/loans/checkout
Headers: `Authorization: Bearer <synthetic-demo-token>`; `Idempotency-Key: 8a6d...`
```json
{"member_id":"00000000-0000-4000-8000-000000000001","item_id":"00000000-0000-4000-8000-000000000002","rfid_epc":"MOCK-EPC-002","channel":"STAFF_RFID"}
```
Successful `201 Created`:
```json
{"loan_id":"00000000-0000-4000-8000-000000000003","item_id":"00000000-0000-4000-8000-000000000002","member_id":"00000000-0000-4000-8000-000000000001","status":"ACTIVE","checked_out_at":"2026-11-08T10:00:00Z","due_at":"2026-11-22T10:00:00Z","integration_status":"QUEUED","correlation_id":"demo-corr-101"}
```
`integration_status` does not assert an external ILMS accepted the action. Dates and 14-day period shown only as synthetic demo policy.

### POST /api/v1/rfid/tags/assign
```json
{"item_id":"00000000-0000-4000-8000-000000000002","epc":"MOCK-EPC-002","reader_id":"MOCK-STAFF-01"}
```
`201`: `{"tag_id":"00000000-0000-4000-8000-000000000011","item_id":"00000000-0000-4000-8000-000000000002","epc":"MOCK-EPC-002","security_armed":true}`. Reject unknown item, duplicate EPC, or an item already tagged without retag workflow.

### POST /api/v1/rfid/gate-events
```json
{"source_event_id":"GATE-0007","reader_id":"MOCK-GATE-01","epc":"MOCK-EPC-002","security_armed":true,"occurred_at":"2026-11-08T11:00:00Z","offline_capture":true}
```
`202`: `{"event_id":"00000000-0000-4000-8000-000000000015","status":"PROVISIONAL","alarm_queued":true}`. Replays with identical `source_event_id` deduplicated.

### POST /api/v1/migration/batches
Metadata: filename, SHA256, category, schema_version; spreadsheet submitted as validated multipart upload with size/content limits (NOT a path supplied by a user). `201`: `{"batch_id":"...","status":"STAGED","source_count":20000}`. Validation returns `accepted_count`, `rejected_count`, `duplicate_count` and download location for error report; reports never contain real PII in candidate demo.

## Common errors
```json
{"error":{"code":"MEMBER_BLOCKED","message":"Member is not eligible for checkout","details":{},"correlation_id":"demo-corr-101"}}
```
400 malformed payload; 401 unauthenticated; 403 permission denied; 404 unknown ID; 409 active-loan/tag conflict, stale version or idempotency-key collision; 422 validation failure; 429 throttled; 503 adapter unavailable (without falsely reporting transaction committed). Never put raw exception text in responses.

## Interface versioning
Additive fields permitted within v1; breaking changes require `/api/v2` and schema migration. Contract tests validate OpenAPI schema, example payloads, authorization matrix, pagination, idempotency and errors. Generated OpenAPI specification is an implementation deliverable, not yet generated.

## API Design Review - 2026-11-08

Status: REVIEWED WITH CHANGES REQUIRED.
All items below are design decisions, not implemented APIs.

### API-01: Method-level authorization
Each HTTP method must have an explicit permission.
GET uses read permission; POST/PATCH use write permission.
Self-service access requires resource ownership checks.
Administrative access requires explicit elevated permissions.
Authorization must be enforced server-side.

### API-02: Idempotency
Require Idempotency-Key for checkout, renewal, return,
tag assignment, retagging, and migration commit.
Gate events use source_event_id for deduplication.

Scope keys to the authenticated principal and operation.
Store a canonical request hash and committed response.
Identical retries return the stored result.
Key reuse with a different request returns 409.
Concurrent identical requests must not execute twice.
Expired keys and retention policy must be configurable.

### API-03: Transaction and adapter failure handling
A checkout commits loan, item state, audit event,
outbox event and idempotency result atomically.

External RFID/ILMS synchronization happens after commit.
Failure after local commit must not return an ambiguous
503 suggesting that checkout was rolled back.
Return the local committed result with QUEUED or
FAILED_RETRYABLE integration status as appropriate.
Use 503 only when local operation cannot be completed
because of an unavailable required dependency.

### API-04: Error contracts
Return 409 for active-loan, duplicate-tag, stale-version
or conflicting idempotency-key operations.

Use 401 for missing/invalid authentication.
Use 403 for insufficient permissions.
Use 422 for valid JSON failing semantic validation.
Error responses must contain stable machine-readable
codes and correlation IDs without exposing secrets.

### API-05: Authentication lifecycle
Define short-lived access tokens or secure sessions.
Define expiration, logout invalidation and revocation.
Store password hashes using an approved password
hashing algorithm; never store plaintext credentials.
Apply login rate limits and account protection.
Cookie authentication requires CSRF protection.
Browser token storage and CORS policy must be documented.

### API-06: Inventory finalization
Add:
POST /inventory/sessions/{id}/finalize
Permission: inventory:write

Finalization calculates missing and misplaced items
from a consistent expected inventory snapshot.
Finalized sessions are immutable except through
a documented administrative correction workflow.
GET reconciliation returns the finalized results.
Repeat finalization must not duplicate results.

### API-07: Migration contracts
POST /migration/batches accepts bounded multipart uploads,
not a filesystem path from an untrusted client.
Validate file type, size, format and row contents.
Reject unexpected spreadsheet formulas and unsafe values.
Commit requires validated/dry-run-ready batch state.
Define atomicity and rollback scope explicitly.
Reconciliation must distinguish inserted, updated,
rejected, duplicate and unchanged records.

### API-08: Pagination, privacy and auditing
Define stable ordering and opaque cursor semantics.
Use deterministic tie-breaking by immutable ID.
Cursors must be scoped to filters and authorized data.
Field-level permissions protect sensitive member data.
Administrative and circulation mutations create
redacted, append-only audit records.
API contract tests must verify all rules above.

### Review disposition
Initial API design review complete.
Final approval pending contract updates, cross-document
consistency review and design verification.
