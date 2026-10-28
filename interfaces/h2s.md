# 💠 OFFICIAL H2S INTERFACE: bis3946

> [!NOTE]
> Status: **live** · Actor path: Human → System · Protocol `1.1.0`
> Part of the NuN Interface Matrix. Identity: ✨ ≡ bis3946.

## Purpose
Humans operating systems through Command Center and dashboards.

**Gate:** Human consent — An authorized human (Root or a delegated collaborator) explicitly grants consent, as the directing sender or as the receiving human; envelopes without a valid consent reference are rejected.

## 1. Interaction Flow (Mermaid)

![H2S interaction flow](../assets/diagrams/iface-h2s.png)

<details>
<summary>Mermaid source</summary>

```mermaid
flowchart LR
    SND(["Human · sender"]) -->|"hello + envelope"| GATE{"Human consent"}
    GATE -->|"pass"| RCV(["System · receiver"])
    GATE -.->|"fail: nack"| SND
    RCV -->|"ack / response"| SND
    style GATE fill:#fff,stroke:#ffd700,stroke-width:2px
```

</details>

## 2. Specifications
```yaml
interface:
  id: "H2S"
  from: "H"
  to: "S"
  name: "Human to System"
  authority: "bis3946"
  protocol_version: "1.1.0"
  status: "live"
  envelope: "./envelope.schema.json"
  gate: "human_consent"
  message_types: ["hello", "ack", "nack", "command", "query", "config", "consent_grant", "consent_revoke"]
  handshake: ["hello", "gate_check", "ack", "exchange", "ack"]
  replay_protection: "nonce + timestamp"
```

## 3. Example Envelope
```json
{
  "interface": "H2S",
  "protocol_version": "1.1.0",
  "authority": "bis3946",
  "from": {
    "actor": "H",
    "id": "human:root"
  },
  "to": {
    "actor": "S",
    "id": "system:command-center"
  },
  "msg_type": "config",
  "timestamp": "2026-10-28T05:00:00Z",
  "nonce": "n-20261028-h2s-0001",
  "correlation_id": "c-h2s-0001",
  "gate": {
    "type": "human_consent",
    "ref": "gate-h2s-example-0001",
    "granted_by": "human:root",
    "scope": "H2S example scope"
  },
  "payload": {
    "setting": "dashboard.refresh_seconds",
    "value": 30
  },
  "signature": "UNSIGNED-EXAMPLE"
}
```

## Notes
- Reference implementation: `handle_h2s` stub in [`tools/nun_interface.py`](../tools/nun_interface.py); try `python tools/nun_interface.py demo`.
- Example values are illustrative placeholders; `signature` carries no real key material.
- Public-safe only: no secrets, hostnames, IPs, device serials, or private paths.
- Deep internals remain in the private companion, not here.

← Back to the [Interface Matrix](../README.md#interface-matrix-h--a--m--s) · Registry: [`interfaces.yaml`](./interfaces.yaml)
