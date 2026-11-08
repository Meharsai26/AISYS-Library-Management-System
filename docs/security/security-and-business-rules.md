# Business Rules, Security, Migration and Resilience v0.1
Status: proposed, unapproved institutional policies.

## Circulation business rules
BR01 authenticated operator needs `circulation:write`; patron cannot issue own loan unless explicitly configured. BR02 member ACTIVE and not expired. BR03 item AVAILABLE and not reference; no active loan. BR04 unpaid outstanding fines (calculated from fines) must not exceed configurable fine threshold. BR05 user quota and maximum simultaneous loans configurable. BR06 checkout duration is a configurable calendar period in local business timezone, stored UTC; holidays/closures undecided. BR07 renewal count max configurable; disallow if overdue, held/reserved (when holds module exists), blocked, or fines over limit. BR08 return only active loan and compute overdue fine by policy (demo may set zero; no institutional rate assumed). BR09 every state-changing attempt produces auditable success/denial outcome without logging private detail. BR10 reference items may be inventoried/tagged but not loaned. BR11 retag requires existing item and privileged operator; keep history. BR12 gate alarm from armed security bit is provisional when ILMS offline; reconcile when back online.

Illustrative synthetic config only: `loan_days=14`, `renewal_max=2`, `fine_limit_minor=5000`, `max_active_loans=5`, currency `INR` for demo only. These are not official AISYS institutional policies and should stay configurable. Explicitly record CL03 until library confirms rules.

## RBAC permissions
| Role | Scope |
|---|---|
| ADMIN | users/roles/config/audit/backup (separate explicit safeguards for destructive operations) |
| LIBRARIAN | catalog read, member read/update, circulation write, tag read, reports |
| CATALOGUER | catalog write, item create/update, tag write; no member private details |
| INVENTORY | inventory read/write, tag read, gate read; no loan write |
| PATRON | public catalog and own loans/preferences only |
| DEVICE | dedicated gate ingest only, no interactive permissions |
Deny by default; authorization checks on every route and domain use case. `ADMIN` not automatically entitled to bypass audit or restore without elevated approval. User/account deactivation revokes sessions. Smart-card tokens map to a pre-existing account; physical possession alone does not grant roles. For demonstration, use synthetic local authentication; production SSO/MFA remains optional design target pending review.

## Security and privacy design
Passwords hashed with a modern password hashing library (Argon2id recommended); secure cookie `HttpOnly`, `Secure`, `SameSite` in deployed HTTPS mode, idle expiration and CSRF controls; avoid persistent tokens in localStorage. Rate-limit login and log blocked attempts. Credentials supplied through process environment/secure host secret store, sample `.env.example` without actual secrets. Parameterized queries, ORM validation, input size limits, spreadsheet formula injection mitigation on exported CSV, upload allowlist and file-size cap. HTTPS between browser and server, protected LAN between services; encryption at rest/backup with managed key external to bundle when real data. Synthetic data only in evaluation. Audit logs: action, actor, reason, timestamp, resource, result, correlation ID; mask personal fields; retention configurable, immutable/append-only permissions. Role and restore operations require restricted accounts.
Threats: tag spoof/replay, counterfeit smart card, unauthorized API calls, privilege escalation, duplicate RFID events, CSRF, malicious spreadsheet upload, untrusted text injection in reports, backup theft, device queue exhaustion, external ILMS accidental writes, and log exposure. Controls: unique source event IDs, authentication, RBAC, content validation, limited privilege, redaction, checksums, offline backups, restore drills and tests. No penetration assessment has occurred.

## Authoritative security and transaction controls

### Session and account lifecycle
Demo authentication uses synthetic identities.
Sessions have configurable idle and absolute expiration.
Logout and account deactivation invalidate active sessions.
Server-side checks enforce authorization on every request.
Browser cookie sessions require CSRF protection.

### Resource authorization
Permissions follow deny-by-default rules.
Patron access to loans, fines and preferences requires
ownership of the requested member resource.
User-role modifications require privileged authorization
and redacted audit records.
Devices have separate credentials and restricted permissions.

### Circulation transaction and audit
Checkout, renewal and return validate eligibility within
a concurrency-safe database transaction.

Successful mutations atomically persist business changes,
required audit records and outbox events.
Idempotency results are included in that transaction.

Business-rule denials do not create loans or modify
circulation state. Record a redacted denial audit event
through a separate controlled transaction.

If a mandatory audit write fails, a successful
circulation mutation must not be committed.

### Migration result accounting
source_count =
accepted_count + rejected_count + duplicate_count

accepted_count =
inserted_count + updated_count + unchanged_count

Updates do not normally increase the target row count.
Verify updated records through stable keys and field-level
or canonical row comparisons.

The prototype uses an all-or-nothing SQLite transaction
for the committed demonstration batch.
A future chunked production strategy requires a separate
checkpoint and compensation design.

### Recovery verification
Verify backup checksum and metadata before restoration.
Restore to an isolated environment first.
Check database integrity, foreign keys, expected counts,
representative records and application queries.
Keep recovery audit evidence outside the restored database.

### Offline update safeguards
Verify package hashes and available pinned dependencies.
Back up the database before schema or application updates.
Retain the previous compatible application release.
Use verified backup restoration for irreversible migrations.
Offline install and rollback are unverified until executed.
## Migration workflow (~20,000 spreadsheet rows)
1. Back up/verify target demo DB; record baseline row counts and SHA256 manifest. Existing ILMS remains untouched/read-only.
2. Accept synthetic Excel/CSV to local controlled staging (not SQL direct). Validate expected headers, encoding, types, ranges, row counts, mandatory keys and duplicates across file/target; quarantine spreadsheet formulas.
3. Normalize whitespace and identifiers, preserve external source keys, produce row-level validation errors. Policy for duplicates: exact duplicate -> `DUPLICATE`; conflicting keys -> `REJECTED` until resolved.
4. Dry run generates accepted/rejected/duplicate totals and proposed inserts/updates, no target changes.
5. Operator authorizes commit; import in bounded transactions with stable deterministic source-to-target keys. Never overwrite legacy source ILMS. In demo prefer atomic all-or-nothing batch; if chunking is necessary, use batch checkpoints and explicit compensation plan.
6. Reconcile `source_count = accepted_count + rejected_count + duplicate_count`; also distinguish accepted rows that become `inserted` vs `unchanged`; target count delta matches inserted minus valid updates. Produce hash/row counts and error CSV.
7. On exception rollback transaction; if backup restore necessary, restrict access, verify restore to disposable copy first, then compare baseline manifest. Retain audit and incident record separately.
8. Dry-run and sample 20k synthetic rows are plans, not claimed validated performance.

## Backup and restore workflows
- Before any destructive migration/update: quiesce writers; create transactionally consistent snapshot of SQLite database using SQLite backup API (NOT simple copying live DB); PostgreSQL target uses documented pg_dump/pg_restore or approved physical backup strategy with compatibility checks. Store encrypted backup separate from live directory; verify SHA256 and restore readability in isolated temp destination.
- Manifest includes timestamp UTC, app/schema versions, database engine, backup tool version, SHA256, row counts for critical tables, operator, reason, and restore prerequisites. No secrets in manifest.
- Restore requires maintenance mode and pre-restore backup of current state. Check checksum, restore into isolated target, run integrity/FK checks and baseline counts/checksums, then controlled cutover; rollback if mismatch. Audit must not be overwritten without retention plan; export incidents outside restored DB.
- Backup and restore are designed but NO recovery point objective/recovery time objective is verified. Candidate planning targets (not guarantees): RPO <= 24 h, RTO <= 4 h; require site sign-off.

## Offline activation, update and rollback design
- Package pinned Python wheels, Node-built static UI, platform installers/runtimes subject to licenses, SBOM, hashes, signed or checksum-verified release manifest, `.env.example`, schema migration notes, admin/user guides and tests.
- Offline preflight: OS architecture, Python/runtime versions, free disk, TCP port allocation, database health, backup storage, credential injection, no external DNS resolution needed.
- Validate package hash/signature, backup, stop writes, apply versioned migration in controlled maintenance window, deploy backend/static files, health/reconciliation checks, keep previous binaries. Reverse migration only when safe; otherwise restore verified backup and previous binaries. Capture version before/after and logs.
- Windows Server 2022+, offline update and rollback are DESIGN ONLY until verified in an isolated Windows environment.

## Verification design and acceptance mapping
| AC | Review/test evidence required (not executed) |
|---|---|
| AC01 | 20k synthetic staging + duplicate/invalid reconciliation |
| AC02 | valid item -> unique mock tag; invalid/duplicate rejected |
| AC03 | checkout-renew-return + mock protocol + audit |
| AC04 | reference, blocked, fine limit all deny atomic checkout |
| AC05 | handheld shelf missing/misplaced reconciliation + feedback |
| AC06 | offline gate alarm, provisional incident, photo/email mock |
| AC07 | smart card mapping + 403 negative authorization |
| AC08 | multi-dimension filtered dashboard from stored facts |
| AC09 | disconnected installation, upgrade, rollback evidence |
| AC10 | verified backup, failed migration, restore and checksum parity |

Additional test categories: API contract, concurrency race, outbox retry/dedup, security negatives, migration interruption, cross-engine portability, performance, offline update. A proposed test ID does not mean a test exists or passed.

## Security and Operations Review - 2026-11-08

Status: REVIEWED WITH CHANGES REQUIRED.
No implementation or security testing is claimed.

### SEC-01: Authentication lifecycle
Define configurable idle and absolute session timeouts.
Revoke sessions on logout and account deactivation.
Enforce server-side session validation.
Require secure password hashing and login rate limiting.
Production identity integration remains unverified.

### SEC-02: Authorization enforcement
Enforce permissions in both API and application layers.
Use resource ownership checks for patron operations.
Deny access by default.
Prevent privilege escalation through role changes.
Audit administrative permission modifications.

### SEC-03: Circulation and auditing
Validate borrower and item eligibility atomically.
Prevent concurrent checkout of the same physical item.
A denied checkout must not create an active loan.
Record business-rule denials using redacted audit events.
Handle failed transactions without recording false success.
Ensure mandatory audit-write failure prevents committing
a successful state-changing circulation transaction.

### SEC-04: Migration reconciliation
Track inserted, updated, unchanged, rejected and
duplicate source records separately.

Updates normally do not change target row counts.
Verify updated records using stable keys and field-level
or canonical row comparisons.

Define all-or-nothing transaction semantics for the
SQLite demonstration batch.
Do not claim atomic multi-batch commits when chunking.
Prevent repeated imports from duplicating target records.

### SEC-05: Backup and restore verification
Use transactionally consistent database backups.
Validate checksums and required backup metadata.
Perform isolated test restores before production cutover.
Verify database integrity, foreign keys, row counts,
selected records and representative application queries.

Protect backup encryption keys separately.
Record restore attempts, failures and verification results.
RPO and RTO remain proposed targets, not measured results.

### SEC-06: Offline lifecycle and rollback
Verify package integrity and dependency availability.
Document supported operating systems and runtimes.
Perform pre-update database backup and health checks.
Retain the previous compatible application release.
For irreversible schema changes, use a verified
backup-based recovery plan instead of unsafe downgrade.

Offline installation, upgrades and rollback remain
unverified until demonstrated in an isolated environment.

### Review disposition
Initial security and operations review complete.
Final design approval requires applying the corrections
and verifying consistency across all design documents.
