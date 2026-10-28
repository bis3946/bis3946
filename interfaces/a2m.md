# 💠 OFFICIAL A2M INTERFACE: bis3946

> [!NOTE]
> Status: **live** · Actor path: Agent → Machine · Protocol `1.1.0`
> Part of the NuN Interface Matrix. Identity: ✨ ≡ bis3946.

## Purpose
Agents commanding and reading machines.

**Gate:** Root authority gate — Acting on machines or constraining agents requires a grant issued under Root authority (bis3946); the grant reference and scope travel in the envelope.

## 1. Interaction Flow (Mermaid)

```mermaid
flowchart LR
    SND(["Agent · sender"]) -->|"hello + envelope"| GATE{"Root authority gate"}
    GATE -->|"pass"| RCV(["Machine · receiver"])
    GATE -.->|"fail: nack"| SND
    RCV -->|"ack / response"| SND
    style GATE fill:#fff,stroke:#ffd700,stroke-width:2px
```

## 2. Specifications
```yaml
interface:
  id: "A2M"
  from: "A"
  to: "M"
  name: "Agent to Machine"
  authority: "bis3946"
  protocol_version: "1.1.0"
  status: "live"
  envelope: "./envelope.schema.json"
  gate: "root_authority_gate"
  message_types: ["hello", "ack", "nack", "command", "query", "response", "heartbeat"]
  handshake: ["hello", "gate_check", "ack", "exchange", "ack"]
  replay_protection: "nonce + timestamp"
```

## 3. Example Envelope
```json
{
  "interface": "A2M",
  "protocol_version": "1.1.0",
  "authority": "bis3946",
  "from": {
    "actor": "A",
    "id": "agent:ana"
  },
  "to": {
    "actor": "M",
    "id": "machine:edge-node-a"
  },
  "msg_type": "command",
  "timestamp": "2026-10-28T05:00:00Z",
  "nonce": "n-20261028-a2m-0001",
  "correlation_id": "c-a2m-0001",
  "gate": {
    "type": "root_authority_gate",
    "ref": "gate-a2m-example-0001",
    "granted_by": "bis3946",
    "scope": "A2M example scope"
  },
  "payload": {
    "action": "read_sensor",
    "target_class": "edge-node",
    "params": {
      "channel": "temperature"
    }
  },
  "signature": "UNSIGNED-EXAMPLE"
}
```

## Notes
- Reference implementation: `handle_a2m` stub in [`tools/nun_interface.py`](../tools/nun_interface.py); try `python tools/nun_interface.py demo`.
- Example values are illustrative placeholders; `signature` carries no real key material.
- Public-safe only: no secrets, hostnames, IPs, device serials, or private paths.
- Deep internals remain in the private companion, not here.

← Back to the [Interface Matrix](../README.md#interface-matrix-h--a--m--s) · Registry: [`interfaces.yaml`](./interfaces.yaml)
