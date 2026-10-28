# 💠 OFFICIAL H2H INTERFACE: bis3946

> [!NOTE]
> Status: **live** · Actor path: Human → Human · Protocol `1.1.0`
> Part of the NuN Interface Matrix. Identity: ✨ ≡ bis3946.

## Purpose
Human collaboration protocols (public-safe).

**Gate:** Mutual consent — Both humans opt in; either side can revoke at any time.

## 1. Interaction Flow (Mermaid)

```mermaid
flowchart LR
    SND(["Human · sender"]) -->|"hello + envelope"| GATE{"Mutual consent"}
    GATE -->|"pass"| RCV(["Human · receiver"])
    GATE -.->|"fail: nack"| SND
    RCV -->|"ack / response"| SND
    style GATE fill:#fff,stroke:#ffd700,stroke-width:2px
```

## 2. Specifications
```yaml
interface:
  id: "H2H"
  from: "H"
  to: "H"
  name: "Human to Human"
  authority: "bis3946"
  protocol_version: "1.1.0"
  status: "live"
  envelope: "./envelope.schema.json"
  gate: "mutual_consent"
  message_types: ["hello", "ack", "query", "response", "report", "consent_request", "consent_grant", "consent_revoke"]
  handshake: ["hello", "gate_check", "ack", "exchange", "ack"]
  replay_protection: "nonce + timestamp"
```

## 3. Example Envelope
```json
{
  "interface": "H2H",
  "protocol_version": "1.1.0",
  "authority": "bis3946",
  "from": {
    "actor": "H",
    "id": "human:root"
  },
  "to": {
    "actor": "H",
    "id": "human:collaborator"
  },
  "msg_type": "query",
  "timestamp": "2026-10-28T05:00:00Z",
  "nonce": "n-20261028-h2h-0001",
  "correlation_id": "c-h2h-0001",
  "gate": {
    "type": "mutual_consent",
    "ref": "gate-h2h-example-0001",
    "granted_by": "human:root,human:collaborator"
  },
  "payload": {
    "topic": "Joint review of interface spec 1.1.0",
    "channel": "public"
  },
  "signature": "UNSIGNED-EXAMPLE"
}
```

## Notes
- Reference implementation: `handle_h2h` stub in [`tools/nun_interface.py`](../tools/nun_interface.py); try `python tools/nun_interface.py demo`.
- Example values are illustrative placeholders; `signature` carries no real key material.
- Public-safe only: no secrets, hostnames, IPs, device serials, or private paths.
- Deep internals remain in the private companion, not here.

← Back to the [Interface Matrix](../README.md#interface-matrix-h--a--m--s) · Registry: [`interfaces.yaml`](./interfaces.yaml)
