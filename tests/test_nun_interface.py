"""Tests for tools/nun_interface.py (stdlib unittest).

Six tests are generated per interface (16 x 6 = 96), plus general tests.
Test names end in _<scheme> (e.g. test_route_accepts_a2m) so results can be
counted per interface.
"""
import hashlib
import io
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import nun_interface as ni  # noqa: E402

ALL_IDS = [f"{a}2{b}" for a in "AHMS" for b in "AHMS"]


class TestGeneral(unittest.TestCase):
    def test_registry_has_16_live_interfaces(self):
        self.assertEqual(sorted(ni.REGISTRY), sorted(ALL_IDS))
        self.assertTrue(all(s.status == "live" for s in ni.REGISTRY.values()))

    def test_every_interface_has_handler(self):
        self.assertEqual(sorted(ni.HANDLERS), sorted(ALL_IDS))

    def test_interface_pattern(self):
        for good in ALL_IDS:
            self.assertTrue(ni.INTERFACE_PATTERN.match(good))
        for bad in ("X2A", "A2X", "AA", "a2a", "A2AA", "H2"):
            self.assertIsNone(ni.INTERFACE_PATTERN.match(bad))

    def test_gate_policy(self):
        g = {k: v.gate for k, v in ni.REGISTRY.items()}
        for sid in ("A2M", "S2M", "S2A"):
            self.assertEqual(g[sid], "root_authority_gate")
        for sid in ("H2A", "A2H", "M2H", "S2H"):
            self.assertEqual(g[sid], "human_consent")
        self.assertEqual(g["H2H"], "mutual_consent")

    def test_signature_not_part_of_digest(self):
        env = ni.example_envelope("A2A")
        d1 = env.digest()
        env.signature = "SOMETHING-ELSE"
        self.assertEqual(d1, env.digest())

    def test_digest_matches_manual_sha3(self):
        env = ni.example_envelope("M2M")
        body = env.to_dict()
        body.pop("signature")
        manual = hashlib.sha3_256(json.dumps(body, sort_keys=True, separators=(",", ":"),
                                             ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(env.digest(), manual)

    def test_dict_roundtrip(self):
        env = ni.example_envelope("H2S")
        self.assertEqual(ni.Envelope.from_dict(env.to_dict()).to_dict(), env.to_dict())

    def test_from_dict_rejects_invalid(self):
        bad = ni.example_envelope("H2S").to_dict()
        bad["interface"] = "X2S"
        with self.assertRaises(ni.EnvelopeError):
            ni.Envelope.from_dict(bad)

    def test_route_dict_rejects_unexpected_field(self):
        bad = ni.example_envelope("S2S").to_dict()
        bad["secret"] = "x"
        self.assertEqual(ni.Router().route(bad).status, "rejected")

    def test_policy_gate_blocks_unsafe_payload(self):
        env = ni.example_envelope("A2S")
        env.payload = {"target": "10.0.0.1"}
        r = ni.Router().route(env)
        self.assertEqual(r.status, "rejected")
        self.assertIn("public-safe", r.reason)

    def test_mutual_consent_needs_two_humans(self):
        env = ni.example_envelope("H2H")
        env.gate.granted_by = "human:root"
        self.assertEqual(ni.Router().route(env).status, "rejected")

    def test_untrusted_peer_rejected(self):
        env = ni.example_envelope("M2M")
        env.from_.id = "machine:unknown-peer"
        self.assertEqual(ni.Router().route(env).status, "rejected")

    def test_bad_timestamp_rejected(self):
        env = ni.example_envelope("S2H")
        env.timestamp = "yesterday"
        self.assertEqual(ni.Router().route(env).status, "rejected")

    def test_demo_cli_accepts_all_16(self):
        buf = io.StringIO()
        self.assertEqual(ni.demo(out=buf), 0)
        out = buf.getvalue()
        self.assertIn("16/16 interfaces accepted", out)
        self.assertEqual(out.count("sha3-256="), 16)

    def test_main_usage_returns_2(self):
        stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            self.assertEqual(ni.main([]), 2)
        finally:
            sys.stdout = stdout


class TestPerInterface(unittest.TestCase):
    """Populated below with six tests per interface."""


def _make_tests(sid):
    def test_route_accepts(self):
        r = ni.Router().route(ni.example_envelope(sid))
        self.assertEqual(r.status, "accepted", r.reason)
        self.assertEqual(r.ack, "ack")
        self.assertEqual(r.handler, f"handle_{sid.lower()}")
        self.assertEqual(r.result["handled_by"], sid)

    def test_receipt_digest_sha3_deterministic(self):
        r1 = ni.Router().route(ni.example_envelope(sid))
        r2 = ni.Router().route(ni.example_envelope(sid))
        self.assertEqual(len(r1.digest), 64)
        self.assertEqual(r1.digest, r2.digest)
        self.assertEqual(r1.digest, ni.example_envelope(sid).digest())

    def test_rejects_wrong_gate_type(self):
        env = ni.example_envelope(sid)
        env.gate.type = next(g for g in ni.GATES if g != ni.REGISTRY[sid].gate)
        r = ni.Router().route(env)
        self.assertEqual(r.status, "rejected")
        self.assertIn("gate", r.reason)

    def test_rejects_unauthorized(self):
        env = ni.example_envelope(sid)
        gate = ni.REGISTRY[sid].gate
        if gate in ("human_consent", "root_authority_gate", "mutual_consent"):
            env.gate.granted_by = "agent:impostor"
        elif gate == "peer_attestation":
            env.from_.id = f"{env.from_.id.split(':')[0]}:not-attested"
        else:  # policy_check
            env.payload = {"leak": "-----BEGIN PRIVATE KEY-----"}
        self.assertEqual(ni.Router().route(env).status, "rejected")

    def test_rejects_replayed_nonce(self):
        router = ni.Router()
        self.assertEqual(router.route(ni.example_envelope(sid)).status, "accepted")
        r = router.route(ni.example_envelope(sid))
        self.assertEqual(r.status, "rejected")
        self.assertIn("replay", r.reason)

    def test_rejects_disallowed_msg_type_and_actor_mismatch(self):
        env = ni.example_envelope(sid)
        env.msg_type = next(m for m in ni.MSG_TYPES if m not in ni.REGISTRY[sid].message_types)
        self.assertEqual(ni.Router().route(env).status, "rejected")
        env2 = ni.example_envelope(sid)
        other = next(a for a in "HAMS" if a != sid[0])
        env2.from_.actor = other
        self.assertEqual(ni.Router().route(env2).status, "rejected")

    for fn in (test_route_accepts, test_receipt_digest_sha3_deterministic, test_rejects_wrong_gate_type,
               test_rejects_unauthorized, test_rejects_replayed_nonce,
               test_rejects_disallowed_msg_type_and_actor_mismatch):
        setattr(TestPerInterface, f"{fn.__name__}_{sid.lower()}", fn)


for _sid in ALL_IDS:
    _make_tests(_sid)

if __name__ == "__main__":
    unittest.main()
