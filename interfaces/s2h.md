# 💠 OFFICIAL S2H INTERFACE: bis3946

> [!NOTE]
> Status: **live** · Actor path: System → Human · Protocol `1.1.0`
> Part of the NuN Interface Matrix. Identity: ✨ ≡ bis3946.

## Purpose
System status and proofs to humans.

**Gate:** Human consent — An authorized human (Root or a delegated collaborator) explicitly grants consent, as the directing sender or as the receiving human; envelopes without a valid consent reference are rejected.

## 1. Interaction Flow (Mermaid)

```mermaid
flowchart LR
    SND(["System · sender"]) -->|"hello + envelope"| GATE{"Human consent"}
    GATE -->|"pass"| RCV(["Human · receiver"])
    GATE -.->|"fail: nack"| SND
    RCV -->|"ack / response"| SND
    style GATE fill:#fff,stroke:#ffd700,stroke-width:2px
```

## 2. Specifications
```yaml
interface:
  id: "S2H"
  from: "S"
  to: "H"
  name: "System to Human"
  authority: "bis3946"
  protocol_version: "1.1.0"
  status: "live"
  envelope: "./envelope.schema.json"
  gate: "human_consent"
  message_types: ["hello", "ack", "report", "alert", "proof", "consent_request"]
  handshake: ["hello", "gate_check", "ack", "exchange", "ack"]
  replay_protection: "nonce + timestamp"
```

## 3. Example Envelope
```json
{
  "interface": "S2H",
  "protocol_version": "1.1.0",
  "authority": "bis3946",
  "from": {
    "actor": "S",
    "id": "system:command-center"
  },
  "to": {
    "actor": "H",
    "id": "human:root"
  },
  "msg_type": "report",
  "timestamp": "2026-10-28T05:00:00Z",
  "nonce": "n-20261028-s2h-0001",
  "correlation_id": "c-s2h-0001",
  "gate": {
    "type": "human_consent",
    "ref": "gate-s2h-example-0001",
    "granted_by": "human:root",
    "scope": "S2H example scope"
  },
  "payload": {
    "title": "Mesh status",
    "status": "nominal",
    "interfaces_live": 16
  },
  "signature": "UNSIGNED-EXAMPLE"
}
```

## Notes
- Reference implementation: `handle_s2h` stub in [`tools/nun_interface.py`](../tools/nun_interface.py); try `python tools/nun_interface.py demo`.
- Example values are illustrative placeholders; `signature` carries no real key material.
- Public-safe only: no secrets, hostnames, IPs, device serials, or private paths.
- Deep internals remain in the private companion, not here.

← Back to the [Interface Matrix](../README.md#interface-matrix-h--a--m--s) · Registry: [`interfaces.yaml`](./interfaces.yaml)
