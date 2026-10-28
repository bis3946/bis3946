#!/usr/bin/env python3
"""NuN interface reference implementation (public, standard library only).

Models the 16 directed interfaces between the four actor classes
H (Human), A (Agent), M (Machine) and S (System) under authority bis3946:

* ``Envelope``           common message envelope (see interfaces/envelope.schema.json)
* ``REGISTRY``           actor / interface registry (twin of interfaces/interfaces.yaml)
* ``validate_envelope``  structural checks matching the JSON Schema
* ``ConsentGate``        human consent, Root authority, mutual consent,
                         peer attestation and policy gates
* ``Router.route``       dispatches to one handler stub per interface and
                         returns a ``Receipt`` with a SHA3-256 envelope digest

There is no key material here. ``signature`` is a placeholder slot only and is
excluded from the digest. Handlers are stubs: they describe the effect, they do
not touch any real device or service.

CLI:
    python tools/nun_interface.py demo            # one example per interface
    python tools/nun_interface.py validate FILE   # validate + route a JSON envelope
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

PROTOCOL_VERSION = "1.1.0"
AUTHORITY = "bis3946"
SYMBOL = "\u2728"  # ✨ is bound to bis3946
INTERFACE_PATTERN = re.compile(r"^[AHMS]2[AHMS]$")
NONCE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
PARTY_ID_PATTERN = re.compile(r"^[a-z]+:[a-z0-9][a-z0-9._-]{0,62}$")
TIMESTAMP_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$")
MAX_PAYLOAD_BYTES = 4096

ACTORS: Dict[str, str] = {"H": "Human", "A": "Agent", "M": "Machine", "S": "System"}

MSG_TYPES = (
    "hello", "ack", "nack", "command", "query", "response", "event", "telemetry",
    "report", "alert", "consent_request", "consent_grant", "consent_revoke",
    "handoff", "config", "heartbeat", "proof",
)

GATES: Dict[str, str] = {
    "human_consent": "Human consent",
    "root_authority_gate": "Root authority gate",
    "mutual_consent": "Mutual consent",
    "peer_attestation": "Peer attestation",
    "policy_check": "Policy check",
}

GATE_RULES: Dict[str, str] = {
    "human_consent": ("An authorized human (Root or a delegated collaborator) explicitly grants consent, "
                      "as the directing sender or as the receiving human; envelopes without a valid "
                      "consent reference are rejected."),
    "root_authority_gate": ("Acting on machines or constraining agents requires a grant issued under Root "
                            "authority (bis3946); the grant reference and scope travel in the envelope."),
    "mutual_consent": "Both humans opt in; either side can revoke at any time.",
    "peer_attestation": ("Sender identity is attested peer-to-peer (signature slot in the envelope); "
                         "unknown peers are rejected."),
    "policy_check": ("The receiving side applies the published NuN policy (public-safe filter, scope "
                     "limits) before accepting."),
}

# Public-safe filter used by the policy gate (no IPs, keys or tokens in payloads).
_UNSAFE = [
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\b(?:sk|pk)-[A-Za-z0-9-]{16,}"),
]


@dataclass(frozen=True)
class InterfaceSpec:
    id: str
    from_actor: str
    to_actor: str
    purpose: str
    gate: str
    message_types: tuple
    status: str = "live"

    @property
    def detail(self) -> str:
        return f"interfaces/{self.id.lower()}.md"

    @property
    def name(self) -> str:
        return f"{ACTORS[self.from_actor]} to {ACTORS[self.to_actor]}"


def _spec(sid: str, purpose: str, gate: str, types: List[str]) -> InterfaceSpec:
    return InterfaceSpec(sid, sid[0], sid[2], purpose, gate, tuple(types))


REGISTRY: Dict[str, InterfaceSpec] = {s.id: s for s in [
    _spec("A2A", "Agent fleet handoff, shared skills, mesh cognition", "peer_attestation",
          ["hello", "ack", "nack", "handoff", "query", "response", "event", "heartbeat"]),
    _spec("A2H", "Agents reporting and surfacing results to humans", "human_consent",
          ["hello", "ack", "report", "alert", "consent_request", "response"]),
    _spec("A2M", "Agents commanding and reading machines", "root_authority_gate",
          ["hello", "ack", "nack", "command", "query", "response", "heartbeat"]),
    _spec("A2S", "Agents calling system APIs and registries", "policy_check",
          ["hello", "ack", "nack", "query", "response", "event", "report"]),
    _spec("H2A", "Root and authorized humans directing agents", "human_consent",
          ["hello", "ack", "nack", "command", "query", "consent_grant", "consent_revoke"]),
    _spec("H2H", "Human collaboration protocols (public-safe)", "mutual_consent",
          ["hello", "ack", "query", "response", "report", "consent_request", "consent_grant", "consent_revoke"]),
    _spec("H2M", "Humans operating machines through local UI or Command Center", "human_consent",
          ["hello", "ack", "nack", "command", "query", "response"]),
    _spec("H2S", "Humans operating systems through Command Center and dashboards", "human_consent",
          ["hello", "ack", "nack", "command", "query", "config", "consent_grant", "consent_revoke"]),
    _spec("M2A", "Machines feeding telemetry and events to agents", "peer_attestation",
          ["hello", "ack", "telemetry", "event", "alert", "heartbeat"]),
    _spec("M2H", "Machine alerts and telemetry to humans", "human_consent",
          ["hello", "ack", "alert", "telemetry", "report"]),
    _spec("M2M", "Device-to-device telemetry, PoA validation, optical/LiGi links", "peer_attestation",
          ["hello", "ack", "nack", "telemetry", "heartbeat", "proof", "event"]),
    _spec("M2S", "Machines reporting into systems", "peer_attestation",
          ["hello", "ack", "nack", "telemetry", "event", "heartbeat", "report"]),
    _spec("S2A", "Systems dispatching and constraining agents", "root_authority_gate",
          ["hello", "ack", "command", "config", "event", "response"]),
    _spec("S2H", "System status and proofs to humans", "human_consent",
          ["hello", "ack", "report", "alert", "proof", "consent_request"]),
    _spec("S2M", "Systems configuring and governing machines", "root_authority_gate",
          ["hello", "ack", "nack", "config", "command", "query", "response"]),
    _spec("S2S", "Service-to-service mesh contracts", "peer_attestation",
          ["hello", "ack", "nack", "query", "response", "event", "heartbeat"]),
]}

# Illustrative, public-safe example identities and payloads.
EXAMPLE_IDS = {"H": "human:root", "A": "agent:ana", "M": "machine:edge-node-a", "S": "system:command-center"}
EXAMPLE_PEER_IDS = {"H": "human:collaborator", "A": "agent:anna", "M": "machine:edge-node-b",
                    "S": "system:nun-registry"}
EXAMPLES: Dict[str, tuple] = {
    "A2A": ("handoff", {"task_ref": "task-example-001", "summary": "Hand off public README review",
                        "context_scope": "public"}),
    "A2H": ("report", {"title": "Daily fleet summary", "items": 3, "visibility": "public-safe"}),
    "A2M": ("command", {"action": "read_sensor", "target_class": "edge-node", "params": {"channel": "temperature"}}),
    "A2S": ("query", {"resource": "registry/interfaces", "filter": {"status": "live"}}),
    "H2A": ("command", {"instruction": "Prepare a public-safe status report", "deadline": "2026-10-29T12:00:00Z"}),
    "H2H": ("query", {"topic": "Joint review of interface spec 1.1.0", "channel": "public"}),
    "H2M": ("command", {"action": "set_mode", "params": {"mode": "standby"}}),
    "H2S": ("config", {"setting": "dashboard.refresh_seconds", "value": 30}),
    "M2A": ("telemetry", {"metric": "temperature_c", "value": 41.5, "window_s": 60}),
    "M2H": ("alert", {"severity": "warning", "message": "Battery below 20 percent"}),
    "M2M": ("proof", {"kind": "poa_validation", "round": 1, "result": "valid"}),
    "M2S": ("heartbeat", {"uptime_s": 86400, "state": "healthy"}),
    "S2A": ("config", {"constraint": "max_parallel_tasks", "value": 4}),
    "S2H": ("report", {"title": "Mesh status", "status": "nominal", "interfaces_live": 16}),
    "S2M": ("config", {"setting": "telemetry.interval_s", "value": 30}),
    "S2S": ("event", {"event": "registry.updated", "version": "1.2.0"}),
}
DEFAULT_TRUSTED_PEERS = frozenset(set(EXAMPLE_IDS.values()) | set(EXAMPLE_PEER_IDS.values()))


# --------------------------------------------------------------------------- data model
class EnvelopeError(ValueError):
    """Envelope is structurally invalid."""


class GateError(PermissionError):
    """Consent / authority / attestation / policy gate refused the envelope."""


@dataclass
class Party:
    actor: str
    id: str

    def to_dict(self) -> Dict[str, str]:
        return {"actor": self.actor, "id": self.id}


@dataclass
class Gate:
    type: str
    ref: str
    granted_by: Optional[str] = None
    scope: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        d = {"type": self.type, "ref": self.ref}
        if self.granted_by is not None:
            d["granted_by"] = self.granted_by
        if self.scope is not None:
            d["scope"] = self.scope
        return d


@dataclass
class Envelope:
    interface: str
    from_: Party
    to: Party
    msg_type: str
    timestamp: str
    nonce: str
    gate: Gate
    payload: Dict[str, Any] = field(default_factory=dict)
    protocol_version: str = PROTOCOL_VERSION
    authority: str = AUTHORITY
    correlation_id: Optional[str] = None
    signature: Optional[str] = None  # placeholder only, never verified, excluded from digest

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "interface": self.interface,
            "protocol_version": self.protocol_version,
            "authority": self.authority,
            "from": self.from_.to_dict(),
            "to": self.to.to_dict(),
            "msg_type": self.msg_type,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
        }
        if self.correlation_id is not None:
            d["correlation_id"] = self.correlation_id
        d["gate"] = self.gate.to_dict()
        d["payload"] = self.payload
        if self.signature is not None:
            d["signature"] = self.signature
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Envelope":
        errs = validate_envelope(d)
        if errs:
            raise EnvelopeError("; ".join(errs))
        return cls(
            interface=d["interface"], from_=Party(**d["from"]), to=Party(**d["to"]),
            msg_type=d["msg_type"], timestamp=d["timestamp"], nonce=d["nonce"], gate=Gate(**d["gate"]),
            payload=d["payload"], protocol_version=d["protocol_version"], authority=d["authority"],
            correlation_id=d.get("correlation_id"), signature=d.get("signature"))

    def canonical_bytes(self) -> bytes:
        body = self.to_dict()
        body.pop("signature", None)
        return canonical_json(body)

    def digest(self) -> str:
        return hashlib.sha3_256(self.canonical_bytes()).hexdigest()


@dataclass
class Receipt:
    interface: str
    msg_type: str
    nonce: str
    correlation_id: Optional[str]
    digest: str
    status: str  # "accepted" (ack) or "rejected" (nack)
    handler: Optional[str] = None
    result: Dict[str, Any] = field(default_factory=dict)
    reason: Optional[str] = None

    @property
    def ack(self) -> str:
        return "ack" if self.status == "accepted" else "nack"

    def to_dict(self) -> Dict[str, Any]:
        return {"interface": self.interface, "msg_type": self.msg_type, "nonce": self.nonce,
                "correlation_id": self.correlation_id, "digest_sha3_256": self.digest,
                "status": self.status, "ack": self.ack, "handler": self.handler,
                "result": self.result, "reason": self.reason}


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# --------------------------------------------------------------------------- validation
def validate_envelope(env: Any) -> List[str]:
    """Return a list of problems (empty list = valid). Accepts Envelope or dict."""
    d = env.to_dict() if isinstance(env, Envelope) else env
    if not isinstance(d, dict):
        return ["envelope must be an object"]
    errs: List[str] = []
    required = ("interface", "protocol_version", "authority", "from", "to", "msg_type",
                "timestamp", "nonce", "gate", "payload")
    allowed = set(required) | {"correlation_id", "signature"}
    errs += [f"missing '{k}'" for k in required if k not in d]
    errs += [f"unexpected '{k}'" for k in d if k not in allowed]
    if errs:
        return errs
    iface = d["interface"]
    if not (isinstance(iface, str) and INTERFACE_PATTERN.match(iface)):
        errs.append("interface must match ^[AHMS]2[AHMS]$")
    if d["protocol_version"] != PROTOCOL_VERSION:
        errs.append(f"protocol_version must be {PROTOCOL_VERSION}")
    if d["authority"] != AUTHORITY:
        errs.append(f"authority must be {AUTHORITY}")
    for side in ("from", "to"):
        p = d[side]
        if not isinstance(p, dict) or set(p) != {"actor", "id"}:
            errs.append(f"{side} must have exactly actor and id")
            continue
        if p["actor"] not in ACTORS:
            errs.append(f"{side}.actor must be one of H, A, M, S")
        if not (isinstance(p["id"], str) and PARTY_ID_PATTERN.match(p["id"])):
            errs.append(f"{side}.id has invalid format")
    if not errs and isinstance(iface, str) and INTERFACE_PATTERN.match(iface):
        if d["from"]["actor"] != iface[0] or d["to"]["actor"] != iface[2]:
            errs.append("from.actor / to.actor must match the interface letters")
    if d["msg_type"] not in MSG_TYPES:
        errs.append("unknown msg_type")
    elif iface in REGISTRY and d["msg_type"] not in REGISTRY[iface].message_types:
        errs.append(f"msg_type '{d['msg_type']}' not allowed on {iface}")
    ts = d["timestamp"]
    if not (isinstance(ts, str) and TIMESTAMP_PATTERN.match(ts)):
        errs.append("timestamp must be RFC 3339")
    else:
        try:
            datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            errs.append("timestamp is not a valid date-time")
    if not (isinstance(d["nonce"], str) and NONCE_PATTERN.match(d["nonce"])):
        errs.append("nonce must match ^[A-Za-z0-9_-]{16,64}$")
    cid = d.get("correlation_id")
    if cid is not None and not (isinstance(cid, str) and re.match(r"^[A-Za-z0-9_-]{1,64}$", cid)):
        errs.append("correlation_id has invalid format")
    g = d["gate"]
    if not isinstance(g, dict) or not {"type", "ref"} <= set(g) or not set(g) <= {"type", "ref", "granted_by", "scope"}:
        errs.append("gate must have type and ref (optional granted_by, scope)")
    elif g["type"] not in GATES:
        errs.append("unknown gate type")
    if not isinstance(d["payload"], dict):
        errs.append("payload must be an object")
    sig = d.get("signature")
    if sig is not None and not (isinstance(sig, str) and len(sig) <= 1024):
        errs.append("signature must be a string placeholder")
    return errs


# --------------------------------------------------------------------------- gate
class ConsentGate:
    """Applies the gate declared for each interface in REGISTRY."""

    def __init__(self, trusted_peers: Optional[frozenset] = None):
        self.trusted_peers = DEFAULT_TRUSTED_PEERS if trusted_peers is None else frozenset(trusted_peers)

    def check(self, env: Envelope, spec: InterfaceSpec) -> None:
        g = env.gate
        if g.type != spec.gate:
            raise GateError(f"{spec.id} requires gate '{spec.gate}', got '{g.type}'")
        if spec.gate == "human_consent":
            if not (g.granted_by or "").startswith("human:") or not g.scope:
                raise GateError(f"{spec.id}: human consent (granted_by human:*, scope) missing")
        elif spec.gate == "root_authority_gate":
            if g.granted_by != AUTHORITY or not g.scope:
                raise GateError(f"{spec.id}: Root authority grant (granted_by bis3946, scope) missing")
        elif spec.gate == "mutual_consent":
            parties = [p.strip() for p in (g.granted_by or "").split(",") if p.strip()]
            if len(set(parties)) < 2 or not all(p.startswith("human:") for p in parties):
                raise GateError(f"{spec.id}: mutual consent of two humans missing")
        elif spec.gate == "peer_attestation":
            if env.from_.id not in self.trusted_peers:
                raise GateError(f"{spec.id}: sender '{env.from_.id}' is not an attested peer")
        elif spec.gate == "policy_check":
            text = canonical_json(env.payload).decode("utf-8")
            if any(rx.search(text) for rx in _UNSAFE):
                raise GateError(f"{spec.id}: payload fails public-safe policy")


# --------------------------------------------------------------------------- handlers
Handler = Callable[[Envelope], Dict[str, Any]]


def _stub(sid: str, effect: str) -> Handler:
    def handler(env: Envelope) -> Dict[str, Any]:
        return {"handled_by": sid, "effect": effect, "msg_type": env.msg_type,
                "payload_keys": sorted(env.payload)}
    handler.__name__ = f"handle_{sid.lower()}"
    handler.__doc__ = f"Stub handler for {sid} ({REGISTRY[sid].name}): {effect}."
    return handler


HANDLERS: Dict[str, Handler] = {
    "A2A": _stub("A2A", "task handed off to peer agent"),
    "A2H": _stub("A2H", "report surfaced to consenting human"),
    "A2M": _stub("A2M", "machine command queued under Root grant"),
    "A2S": _stub("A2S", "system API call accepted after policy check"),
    "H2A": _stub("H2A", "instruction delivered to agent with human consent"),
    "H2H": _stub("H2H", "collaboration message exchanged by mutual consent"),
    "H2M": _stub("H2M", "operator action applied to machine"),
    "H2S": _stub("H2S", "operator change applied to system"),
    "M2A": _stub("M2A", "machine telemetry delivered to agent"),
    "M2H": _stub("M2H", "machine alert shown to consenting human"),
    "M2M": _stub("M2M", "peer machine message accepted"),
    "M2S": _stub("M2S", "machine report ingested by system"),
    "S2A": _stub("S2A", "system constraint applied to agent under Root grant"),
    "S2H": _stub("S2H", "system status delivered to consenting human"),
    "S2M": _stub("S2M", "system configuration queued for machine under Root grant"),
    "S2S": _stub("S2S", "service contract message accepted"),
}


# --------------------------------------------------------------------------- router
class Router:
    """validate -> resolve interface -> gate -> dispatch -> receipt."""

    def __init__(self, gate: Optional[ConsentGate] = None, handlers: Optional[Dict[str, Handler]] = None):
        self.gate = gate or ConsentGate()
        self.handlers = dict(HANDLERS if handlers is None else handlers)
        self._seen_nonces: set = set()

    def route(self, env: Any) -> Receipt:
        if isinstance(env, dict):
            try:
                env = Envelope.from_dict(env)
            except EnvelopeError as e:
                return Receipt(str(env.get("interface")), str(env.get("msg_type")), str(env.get("nonce")),
                               env.get("correlation_id"), hashlib.sha3_256(canonical_json(env)).hexdigest(),
                               "rejected", reason=f"envelope: {e}")
        digest = env.digest()

        def reject(reason: str) -> Receipt:
            return Receipt(env.interface, env.msg_type, env.nonce, env.correlation_id, digest,
                           "rejected", reason=reason)

        errs = validate_envelope(env)
        if errs:
            return reject("envelope: " + "; ".join(errs))
        spec = REGISTRY.get(env.interface)
        if spec is None or spec.status != "live":
            return reject(f"interface {env.interface} not live")
        if env.nonce in self._seen_nonces:
            return reject("replayed nonce")
        try:
            self.gate.check(env, spec)
        except GateError as e:
            return reject(f"gate: {e}")
        handler = self.handlers.get(env.interface)
        if handler is None:
            return reject(f"no handler for {env.interface}")
        self._seen_nonces.add(env.nonce)
        result = handler(env)
        return Receipt(env.interface, env.msg_type, env.nonce, env.correlation_id, digest,
                       "accepted", handler=getattr(handler, "__name__", "handler"), result=result)


# --------------------------------------------------------------------------- examples / CLI
def example_gate(sid: str) -> Gate:
    gate = REGISTRY[sid].gate
    ref = f"gate-{sid.lower()}-example-0001"
    if gate == "human_consent":
        return Gate(gate, ref, "human:root", f"{sid} example scope")
    if gate == "root_authority_gate":
        return Gate(gate, ref, AUTHORITY, f"{sid} example scope")
    if gate == "mutual_consent":
        return Gate(gate, ref, "human:root,human:collaborator")
    return Gate(gate, ref)


def example_envelope(sid: str) -> Envelope:
    """Deterministic, public-safe example envelope for interface ``sid``."""
    f, t = sid[0], sid[2]
    msg_type, payload = EXAMPLES[sid]
    return Envelope(
        interface=sid,
        from_=Party(f, EXAMPLE_IDS[f]),
        to=Party(t, EXAMPLE_PEER_IDS[t] if f == t else EXAMPLE_IDS[t]),
        msg_type=msg_type,
        timestamp="2026-10-28T05:00:00Z",
        nonce=f"n-20261028-{sid.lower()}-0001",
        gate=example_gate(sid),
        payload=json.loads(json.dumps(payload)),
        correlation_id=f"c-{sid.lower()}-0001",
        signature="UNSIGNED-EXAMPLE",
    )


def demo(out=sys.stdout) -> int:
    router = Router()
    accepted = 0
    print(f"NuN interface demo · authority {AUTHORITY} {SYMBOL} · protocol {PROTOCOL_VERSION}", file=out)
    for sid in REGISTRY:
        r = router.route(example_envelope(sid))
        accepted += r.status == "accepted"
        print(f"{sid}  {r.ack:<4} {r.msg_type:<10} gate={REGISTRY[sid].gate:<20} sha3-256={r.digest}", file=out)
    print(f"{accepted}/{len(REGISTRY)} interfaces accepted", file=out)
    return 0 if accepted == len(REGISTRY) else 1


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["demo"]:
        return demo()
    if len(argv) == 2 and argv[0] == "validate":
        with open(argv[1], encoding="utf-8") as fh:
            receipt = Router().route(json.load(fh))
        print(json.dumps(receipt.to_dict(), indent=2, ensure_ascii=False))
        return 0 if receipt.status == "accepted" else 1
    print(__doc__.strip().split("CLI:")[1].rstrip())
    return 2


if __name__ == "__main__":
    sys.exit(main())
