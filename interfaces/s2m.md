# 💠 OFFICIAL S2M INTERFACE: bis3946

> [!NOTE]
> Status: **live** · Actor path: System → Machine · Protocol `1.1.0`
> Part of the NuN Interface Matrix. Identity: ✨ ≡ bis3946.

## Purpose
Systems configuring and governing machines.

**Gate:** Root authority gate — Acting on machines or constraining agents requires a grant issued under Root authority (bis3946); the grant reference and scope travel in the envelope.

## 1. Interaction Flow (Mermaid)

![S2M interaction flow](../assets/diagrams/iface-s2m.png)

<details>
<summary>Mermaid source</summary>

```mermaid
flowchart LR
    SND(["System · sender"]) -->|"hello + envelope"| GATE{"Root authority gate"}
    GATE -->|"pass"| RCV(["Machine · receiver"])
    GATE -.->|"fail: nack"| SND
    RCV -->|"ack / response"| SND
    style GATE fill:#fff,stroke:#ffd700,stroke-width:2px
```

</details>

## 2. Specifications
```yaml
interface:
  id: "S2M"
  from: "S"
  to: "M"
  name: "System to Machine"
  authority: "bis3946"
  protocol_version: "1.1.0"
  status: "live"
  envelope: "./envelope.schema.json"
  gate: "root_authority_gate"
  message_types: ["hello", "ack", "nack", "config", "command", "query", "response"]
  handshake: ["hello", "gate_check", "ack", "exchange", "ack"]
  replay_protection: "nonce + timestamp"
```

## 3. Example Envelope
```json
{
  "interface": "S2M",
  "protocol_version": "1.1.0",
  "authority": "bis3946",
  "from": {
    "actor": "S",
    "id": "system:command-center"
  },
  "to": {
    "actor": "M",
    "id": "machine:edge-node-a"
  },
  "msg_type": "config",
  "timestamp": "2026-10-28T05:00:00Z",
  "nonce": "n-20261028-s2m-0001",
  "correlation_id": "c-s2m-0001",
  "gate": {
    "type": "root_authority_gate",
    "ref": "gate-s2m-example-0001",
    "granted_by": "bis3946",
    "scope": "S2M example scope"
  },
  "payload": {
    "setting": "telemetry.interval_s",
    "value": 30
  },
  "signature": "UNSIGNED-EXAMPLE"
}
```

## Notes
- Reference implementation: `handle_s2m` stub in [`tools/nun_interface.py`](../tools/nun_interface.py); try `python tools/nun_interface.py demo`.
- Example values are illustrative placeholders; `signature` carries no real key material.
- Public-safe only: no secrets, hostnames, IPs, device serials, or private paths.
- Deep internals remain in the private companion, not here.

← Back to the [Interface Matrix](../README.md#interface-matrix-h--a--m--s) · Registry: [`interfaces.yaml`](./interfaces.yaml)
