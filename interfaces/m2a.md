# 💠 OFFICIAL M2A INTERFACE: bis3946

> [!NOTE]
> Status: **live** · Actor path: Machine → Agent · Protocol `1.1.0`
> Part of the NuN Interface Matrix. Identity: ✨ ≡ bis3946.

## Purpose
Machines feeding telemetry and events to agents.

**Gate:** Peer attestation — Sender identity is attested peer-to-peer (signature slot in the envelope); unknown peers are rejected.

## 1. Interaction Flow (Mermaid)

![M2A interaction flow](../assets/diagrams/iface-m2a.png)

<details>
<summary>Mermaid source</summary>

```mermaid
flowchart LR
    SND(["Machine · sender"]) -->|"hello + envelope"| GATE{"Peer attestation"}
    GATE -->|"pass"| RCV(["Agent · receiver"])
    GATE -.->|"fail: nack"| SND
    RCV -->|"ack / response"| SND
    style GATE fill:#fff,stroke:#ffd700,stroke-width:2px
```

</details>

## 2. Specifications
```yaml
interface:
  id: "M2A"
  from: "M"
  to: "A"
  name: "Machine to Agent"
  authority: "bis3946"
  protocol_version: "1.1.0"
  status: "live"
  envelope: "./envelope.schema.json"
  gate: "peer_attestation"
  message_types: ["hello", "ack", "telemetry", "event", "alert", "heartbeat"]
  handshake: ["hello", "gate_check", "ack", "exchange", "ack"]
  replay_protection: "nonce + timestamp"
```

## 3. Example Envelope
```json
{
  "interface": "M2A",
  "protocol_version": "1.1.0",
  "authority": "bis3946",
  "from": {
    "actor": "M",
    "id": "machine:edge-node-a"
  },
  "to": {
    "actor": "A",
    "id": "agent:ana"
  },
  "msg_type": "telemetry",
  "timestamp": "2026-10-28T05:00:00Z",
  "nonce": "n-20261028-m2a-0001",
  "correlation_id": "c-m2a-0001",
  "gate": {
    "type": "peer_attestation",
    "ref": "gate-m2a-example-0001"
  },
  "payload": {
    "metric": "temperature_c",
    "value": 41.5,
    "window_s": 60
  },
  "signature": "UNSIGNED-EXAMPLE"
}
```

## Notes
- Reference implementation: `handle_m2a` stub in [`tools/nun_interface.py`](../tools/nun_interface.py); try `python tools/nun_interface.py demo`.
- Example values are illustrative placeholders; `signature` carries no real key material.
- Public-safe only: no secrets, hostnames, IPs, device serials, or private paths.
- Deep internals remain in the private companion, not here.

← Back to the [Interface Matrix](../README.md#interface-matrix-h--a--m--s) · Registry: [`interfaces.yaml`](./interfaces.yaml)
