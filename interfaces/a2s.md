# 💠 OFFICIAL A2S INTERFACE: bis3946

> [!NOTE]
> Status: **live** · Actor path: Agent → System · Protocol `1.1.0`
> Part of the NuN Interface Matrix. Identity: ✨ ≡ bis3946.

## Purpose
Agents calling system APIs and registries.

**Gate:** Policy check — The receiving side applies the published NuN policy (public-safe filter, scope limits) before accepting.

## 1. Interaction Flow (Mermaid)

```mermaid
flowchart LR
    SND(["Agent · sender"]) -->|"hello + envelope"| GATE{"Policy check"}
    GATE -->|"pass"| RCV(["System · receiver"])
    GATE -.->|"fail: nack"| SND
    RCV -->|"ack / response"| SND
    style GATE fill:#fff,stroke:#ffd700,stroke-width:2px
```

## 2. Specifications
```yaml
interface:
  id: "A2S"
  from: "A"
  to: "S"
  name: "Agent to System"
  authority: "bis3946"
  protocol_version: "1.1.0"
  status: "live"
  envelope: "./envelope.schema.json"
  gate: "policy_check"
  message_types: ["hello", "ack", "nack", "query", "response", "event", "report"]
  handshake: ["hello", "gate_check", "ack", "exchange", "ack"]
  replay_protection: "nonce + timestamp"
```

## 3. Example Envelope
```json
{
  "interface": "A2S",
  "protocol_version": "1.1.0",
  "authority": "bis3946",
  "from": {
    "actor": "A",
    "id": "agent:ana"
  },
  "to": {
    "actor": "S",
    "id": "system:command-center"
  },
  "msg_type": "query",
  "timestamp": "2026-10-28T05:00:00Z",
  "nonce": "n-20261028-a2s-0001",
  "correlation_id": "c-a2s-0001",
  "gate": {
    "type": "policy_check",
    "ref": "gate-a2s-example-0001"
  },
  "payload": {
    "resource": "registry/interfaces",
    "filter": {
      "status": "live"
    }
  },
  "signature": "UNSIGNED-EXAMPLE"
}
```

## Notes
- Reference implementation: `handle_a2s` stub in [`tools/nun_interface.py`](../tools/nun_interface.py); try `python tools/nun_interface.py demo`.
- Example values are illustrative placeholders; `signature` carries no real key material.
- Public-safe only: no secrets, hostnames, IPs, device serials, or private paths.
- Deep internals remain in the private companion, not here.

← Back to the [Interface Matrix](../README.md#interface-matrix-h--a--m--s) · Registry: [`interfaces.yaml`](./interfaces.yaml)
