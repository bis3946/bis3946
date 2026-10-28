# 💠 OFFICIAL M2S INTERFACE: bis3946

> [!NOTE]
> Status: **live** · Actor path: Machine → System · Protocol `1.1.0`
> Part of the NuN Interface Matrix. Identity: ✨ ≡ bis3946.

## Purpose
Machines reporting into systems.

**Gate:** Peer attestation — Sender identity is attested peer-to-peer (signature slot in the envelope); unknown peers are rejected.

## 1. Interaction Flow (Mermaid)

```mermaid
flowchart LR
    SND(["Machine · sender"]) -->|"hello + envelope"| GATE{"Peer attestation"}
    GATE -->|"pass"| RCV(["System · receiver"])
    GATE -.->|"fail: nack"| SND
    RCV -->|"ack / response"| SND
    style GATE fill:#fff,stroke:#ffd700,stroke-width:2px
```

## 2. Specifications
```yaml
interface:
  id: "M2S"
  from: "M"
  to: "S"
  name: "Machine to System"
  authority: "bis3946"
  protocol_version: "1.1.0"
  status: "live"
  envelope: "./envelope.schema.json"
  gate: "peer_attestation"
  message_types: ["hello", "ack", "nack", "telemetry", "event", "heartbeat", "report"]
  handshake: ["hello", "gate_check", "ack", "exchange", "ack"]
  replay_protection: "nonce + timestamp"
```

## 3. Example Envelope
```json
{
  "interface": "M2S",
  "protocol_version": "1.1.0",
  "authority": "bis3946",
  "from": {
    "actor": "M",
    "id": "machine:edge-node-a"
  },
  "to": {
    "actor": "S",
    "id": "system:command-center"
  },
  "msg_type": "heartbeat",
  "timestamp": "2026-10-28T05:00:00Z",
  "nonce": "n-20261028-m2s-0001",
  "correlation_id": "c-m2s-0001",
  "gate": {
    "type": "peer_attestation",
    "ref": "gate-m2s-example-0001"
  },
  "payload": {
    "uptime_s": 86400,
    "state": "healthy"
  },
  "signature": "UNSIGNED-EXAMPLE"
}
```

## Notes
- Reference implementation: `handle_m2s` stub in [`tools/nun_interface.py`](../tools/nun_interface.py); try `python tools/nun_interface.py demo`.
- Example values are illustrative placeholders; `signature` carries no real key material.
- Public-safe only: no secrets, hostnames, IPs, device serials, or private paths.
- Deep internals remain in the private companion, not here.

← Back to the [Interface Matrix](../README.md#interface-matrix-h--a--m--s) · Registry: [`interfaces.yaml`](./interfaces.yaml)
