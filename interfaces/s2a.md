# 💠 OFFICIAL S2A INTERFACE: bis3946

> [!NOTE]
> Status: **live** · Actor path: System → Agent · Protocol `1.1.0`
> Part of the NuN Interface Matrix. Identity: ✨ ≡ bis3946.

## Purpose
Systems dispatching and constraining agents.

**Gate:** Root authority gate — Acting on machines or constraining agents requires a grant issued under Root authority (bis3946); the grant reference and scope travel in the envelope.

## 1. Interaction Flow (Mermaid)

```mermaid
flowchart LR
    SND(["System · sender"]) -->|"hello + envelope"| GATE{"Root authority gate"}
    GATE -->|"pass"| RCV(["Agent · receiver"])
    GATE -.->|"fail: nack"| SND
    RCV -->|"ack / response"| SND
    style GATE fill:#fff,stroke:#ffd700,stroke-width:2px
```

## 2. Specifications
```yaml
interface:
  id: "S2A"
  from: "S"
  to: "A"
  name: "System to Agent"
  authority: "bis3946"
  protocol_version: "1.1.0"
  status: "live"
  envelope: "./envelope.schema.json"
  gate: "root_authority_gate"
  message_types: ["hello", "ack", "command", "config", "event", "response"]
  handshake: ["hello", "gate_check", "ack", "exchange", "ack"]
  replay_protection: "nonce + timestamp"
```

## 3. Example Envelope
```json
{
  "interface": "S2A",
  "protocol_version": "1.1.0",
  "authority": "bis3946",
  "from": {
    "actor": "S",
    "id": "system:command-center"
  },
  "to": {
    "actor": "A",
    "id": "agent:ana"
  },
  "msg_type": "config",
  "timestamp": "2026-10-28T05:00:00Z",
  "nonce": "n-20261028-s2a-0001",
  "correlation_id": "c-s2a-0001",
  "gate": {
    "type": "root_authority_gate",
    "ref": "gate-s2a-example-0001",
    "granted_by": "bis3946",
    "scope": "S2A example scope"
  },
  "payload": {
    "constraint": "max_parallel_tasks",
    "value": 4
  },
  "signature": "UNSIGNED-EXAMPLE"
}
```

## Notes
- Reference implementation: `handle_s2a` stub in [`tools/nun_interface.py`](../tools/nun_interface.py); try `python tools/nun_interface.py demo`.
- Example values are illustrative placeholders; `signature` carries no real key material.
- Public-safe only: no secrets, hostnames, IPs, device serials, or private paths.
- Deep internals remain in the private companion, not here.

← Back to the [Interface Matrix](../README.md#interface-matrix-h--a--m--s) · Registry: [`interfaces.yaml`](./interfaces.yaml)
