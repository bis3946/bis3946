# 💠 OFFICIAL M2H INTERFACE: bis3946

> [!NOTE]
> Status: **live** · Actor path: Machine → Human · Protocol `1.1.0`
> Part of the NuN Interface Matrix. Identity: ✨ ≡ bis3946.

## Purpose
Machine alerts and telemetry to humans.

**Gate:** Human consent — An authorized human (Root or a delegated collaborator) explicitly grants consent, as the directing sender or as the receiving human; envelopes without a valid consent reference are rejected.

## 1. Interaction Flow (Mermaid)

![M2H interaction flow](../assets/diagrams/iface-m2h.png)

<details>
<summary>Mermaid source</summary>

```mermaid
flowchart LR
    SND(["Machine · sender"]) -->|"hello + envelope"| GATE{"Human consent"}
    GATE -->|"pass"| RCV(["Human · receiver"])
    GATE -.->|"fail: nack"| SND
    RCV -->|"ack / response"| SND
    style GATE fill:#fff,stroke:#ffd700,stroke-width:2px
```

</details>

## 2. Specifications
```yaml
interface:
  id: "M2H"
  from: "M"
  to: "H"
  name: "Machine to Human"
  authority: "bis3946"
  protocol_version: "1.1.0"
  status: "live"
  envelope: "./envelope.schema.json"
  gate: "human_consent"
  message_types: ["hello", "ack", "alert", "telemetry", "report"]
  handshake: ["hello", "gate_check", "ack", "exchange", "ack"]
  replay_protection: "nonce + timestamp"
```

## 3. Example Envelope
```json
{
  "interface": "M2H",
  "protocol_version": "1.1.0",
  "authority": "bis3946",
  "from": {
    "actor": "M",
    "id": "machine:edge-node-a"
  },
  "to": {
    "actor": "H",
    "id": "human:root"
  },
  "msg_type": "alert",
  "timestamp": "2026-10-28T05:00:00Z",
  "nonce": "n-20261028-m2h-0001",
  "correlation_id": "c-m2h-0001",
  "gate": {
    "type": "human_consent",
    "ref": "gate-m2h-example-0001",
    "granted_by": "human:root",
    "scope": "M2H example scope"
  },
  "payload": {
    "severity": "warning",
    "message": "Battery below 20 percent"
  },
  "signature": "UNSIGNED-EXAMPLE"
}
```

## Notes
- Reference implementation: `handle_m2h` stub in [`tools/nun_interface.py`](../tools/nun_interface.py); try `python tools/nun_interface.py demo`.
- Example values are illustrative placeholders; `signature` carries no real key material.
- Public-safe only: no secrets, hostnames, IPs, device serials, or private paths.
- Deep internals remain in the private companion, not here.

← Back to the [Interface Matrix](../README.md#interface-matrix-h--a--m--s) · Registry: [`interfaces.yaml`](./interfaces.yaml)
