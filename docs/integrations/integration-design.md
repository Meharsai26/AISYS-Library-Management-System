# RFID, External Boundaries and Events v0.1 — DESIGN ONLY

## Adapter interfaces (Python-like signatures, not executable implementation)
```python
from typing import Protocol
class RFIDReaderPort(Protocol):
    def read_tags(self, reader_id: str) -> list[dict]: ...
    def write_tag(self, reader_id: str, epc: str, item_ref: str) -> dict: ...
    def set_security_bit(self, epc: str, armed: bool) -> dict: ...

class GatePort(Protocol):
    def emit_passage(self, event: dict) -> dict: ...
class SmartCardPort(Protocol):
    def resolve_card(self, card_token: str) -> dict: ...
class CirculationProtocolPort(Protocol):
    def checkout(self, request: dict) -> dict: ...
    def checkin(self, request: dict) -> dict: ...
    def renew(self, request: dict) -> dict: ...
class ExternalILMSPort(Protocol):
    def find_item(self, external_key: str) -> dict | None: ...
    def find_patron(self, external_key: str) -> dict | None: ...
class NotificationPort(Protocol):
    def enqueue(self, channel: str, template: str, data: dict) -> str: ...
class CameraPort(Protocol):
    def capture_reference(self, gate_event_id: str) -> str: ...
class PrinterPort(Protocol):
    def print_document(self, template: str, fields: dict) -> str: ...
```
Adapters enforce timeouts, validate message shapes, authenticate devices by configured local credentials, and report typed failures. `MockNCIPAdapter` and `MockSIP2Adapter` implement *candidate application semantics only*; they do not purport to speak standards-compliant wire protocol or use real institutional systems. Real vendors require mapping, security, endpoint details, SDK licensing and interoperability validation.

## Authoritative integration behavior

### RFID security state
After a successful local checkout commit, enqueue a
device-neutral request to disarm the assigned RFID tag.

After a successful local return commit, enqueue a
device-neutral request to rearm the assigned RFID tag.

Persist desired state and synchronization status separately
from the loan state. Track PENDING, APPLIED and FAILED
outcomes. Never claim a device operation succeeded before
its adapter acknowledges the command.

### Offline gate buffering
The mock gate uses durable local event storage.
Each event has a stable source_event_id.

Candidate demonstration settings:
- Maximum buffered events: 1000 per gate.
- Retention target: 7 days.
- Retry strategy: bounded exponential backoff.
- Overflow behavior: alert operator and record overflow.

These settings are design assumptions, not approved
institutional operating policies.

An offline alarm is provisional. On reconnection,
queued events are replayed and deduplicated.
The server must tolerate out-of-order delivery.

### Reliable event delivery
Business operations persist outbox events in the same
transaction as their database state changes.

Workers process pending events using bounded retries.
Consumers deduplicate by source identity and event ID.

After retry exhaustion, send the event to a dead-letter
state for operator review.

Delivery is at-least-once, not exactly-once.
External device actions must be idempotent where possible.

### External system protection
External ILMS access is read-only by default.
No adapter may write to existing ILMS records without
an approved integration contract and authorization.

Mock NCIP/SIP2 results are application simulations,
not claims of standards-compliant wire protocols.
## Proposed device envelope
```json
{"event_id":"mock-reader-evt-123","schema_version":1,"device_type":"HANDHELD","device_id":"MOCK-HH-01","event_type":"rfid.tag_observed","occurred_at":"2026-11-08T10:20:00Z","correlation_id":"corr-55","payload":{"epc":"MOCK-EPC-002","shelf_code":"A-01"}}
```
Validate event IDs, allowed device types, timestamp skew, payload size and device authorization. Deduplicate `(device_id,event_id)` in inbox. Treat any unknown tag as unlinked observation, never create unreviewed authoritative item records.

## Event catalogue (event schema v1)
- `catalog.item_created` (item_id, accession_number, bib_id)
- `rfid.tag_assigned` (item_id, epc, reader_id)
- `rfid.tag_observed` (epc, reader_id, scan_session_id)
- `circulation.loan_checked_out` (loan_id, member_id, item_id, due_at)
- `circulation.loan_renewed` (loan_id, old_due_at, new_due_at)
- `circulation.loan_returned` (loan_id, item_id, returned_at)
- `inventory.scan_completed` (session_id, missing_count, misplaced_count)
- `gate.unauthorized_passage_detected` (gate_event_id, epc, provisional, accession_snapshot)
- `notification.delivery_requested` (job_id, channel, template)
- `migration.batch_committed` (batch_id, source_count, accepted_count, rejected_count, duplicate_count)
- `operations.restore_completed` (manifest_id, verification_result)
Every event envelope includes unique event_id, schema_version, occurred_at UTC, correlation_id, actor/device identifier and redaction-aware payload. Event delivery is at-least-once; consumers must be idempotent.

## Gate offline flow and external errors
1. Mock gate caches a signed/validated config and buffered event log within local storage; security bit remains usable even if server unavailable.
2. Passage with armed bit -> local simulated alarm + `PROVISIONAL` event; do not assume an authoritative loan status when offline.
3. Queue bounded by explicit capacity and retention; on capacity exceeded alert operator and retain incident metadata per site policy.
4. On reconnect replay source_event_id once logically; server correlates item, creates audit, adds mock photo reference and queues mock email; final status `RECONCILED`.
5. Simulate timeouts, duplicates, out-of-order events and provider failures. Never retry unboundedly; exponential backoff and dead-letter review.

## External compatibility boundaries
- ILMS adapter read-only mock. Any future write support requires vendor-owned API, authorization, dry-run, backup, record-level provenance, side-by-side reconciliation, and explicit go/no-go.
- NCIP 2.0 and SIP2 port definitions are *boundaries*, not certified implementations or real protocol transcript evidence.
- Email/SMS/print/camera providers return synthetic IDs. Notification output must respect user preferences and suppress if no consent/contact route.
- Printer/labels: template rendering and fake print queue; barcode/spine labels planned, no device driver validation.
- Search/net cataloguing and serials/acquisition have documented modules/ports but broader capability requires future design elaboration and testing.

## Integration Design Review - 2026-11-08

Status: REVIEWED WITH CHANGES REQUIRED.
No physical device or external integration has been tested.

### INT-01: Typed adapter contracts
Use typed request/response models instead of unrestricted
dict payloads at service boundaries.
Define explicit success, timeout, unavailable,
authentication and invalid-response outcomes.
Every adapter operation carries a correlation ID.
Vendor-neutral application models must remain separate
from NCIP, SIP2 or device-specific wire formats.

### INT-02: RFID security-bit lifecycle
Successful local checkout queues a request to disarm
the RFID tag security bit.
Successful local return queues a request to rearm it.
Retagging must preserve the required security state.

Record DESIRED, PENDING, APPLIED or FAILED synchronization
state independently from the local loan transaction.
Never assume a physical tag was successfully changed
without adapter acknowledgement.

### INT-03: Offline gate reliability
Proposed demo queue capacity: 1000 events per gate.
Proposed demo retention: 7 days.
These are candidate defaults, not institutional policy.

Use durable local event storage and stable event IDs.
Raise an operator alert when capacity reaches its limit.
Do not claim lossless retention after capacity exhaustion.
Preserve queued records until acknowledged or explicitly
handled through a documented retention procedure.
Replay in occurrence order where possible, while allowing
server-side processing of out-of-order events.

### INT-04: Outbox and inbox processing
Write outbox events in the same transaction as the
associated business change.
Workers lease pending events and record delivery results.
Consumers deduplicate using source identity and event ID.
Use bounded exponential retries with jitter.
After the configured retry limit, transition the event
to a dead-letter state requiring operator review.
Do not promise exactly-once external delivery.
Notifications and device commands must be idempotent
where their adapters support it.

### INT-05: NCIP and SIP2 mock mapping
Define application operations:
CHECKOUT, CHECKIN and RENEW.

Map each operation to a provider-neutral request/result.
Possible results include ACCEPTED, REJECTED,
TIMEOUT and UNAVAILABLE.

MockNCIPAdapter and MockSIP2Adapter simulate the
application contract only. No wire-format compliance,
OEM certification or production interoperability
is claimed.

External ILMS writes remain disabled by default.

### INT-06: Device and provider security
Authenticate configured devices independently from
ordinary user sessions.
Authorize devices by identity and allowed event type.
Support credential rotation and revocation.
Validate device timestamps, payload sizes and event IDs.
Use TLS where applicable and secure local configuration
for isolated deployments.
Do not store credentials or sensitive provider details
in event payloads or logs.

### Review disposition
Initial integration design review complete.
Final approval pending incorporation of corrections,
cross-document verification and design review.
