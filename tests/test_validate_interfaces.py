"""Tests for tools/validate_interfaces.py: the real package passes, mutations fail."""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import validate_interfaces as vi  # noqa: E402


class TestValidator(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(ROOT, self.tmp / "repo", ignore=shutil.ignore_patterns(".git", "__pycache__"))
        self.repo = self.tmp / "repo"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit(self, rel, old, new, count=1):
        p = self.repo / rel
        text = p.read_text(encoding="utf-8")
        self.assertIn(old, text)
        p.write_text(text.replace(old, new, count), encoding="utf-8")

    def assertFails(self, needle):
        r = vi.validate(self.repo)
        self.assertTrue(any(needle in e for e in r.errors), r.errors)

    def test_real_package_passes(self):
        r = vi.validate(ROOT)
        self.assertEqual(r.errors, [])
        self.assertGreater(r.checks, 500)

    def test_anchor_is_stable_and_published(self):
        a = vi.compute_anchor(ROOT)
        self.assertRegex(a, r"^[0-9a-f]{64}$")
        self.assertIn(a, (ROOT / "README.md").read_text(encoding="utf-8"))

    def test_anchor_detects_identity_change(self):
        self.edit("identity.json", '"version": "1.2.0"', '"version": "9.9.9"')
        self.assertFails("Ontological Anchor")

    def test_anchor_detects_registry_change(self):
        self.edit("interfaces/interfaces.yaml", '"Nexus of Unity (NuN)"', '"Other"')
        self.assertFails("Ontological Anchor")

    def test_status_not_live_fails(self):
        self.edit("interfaces/a2a.md", 'status: "live"', 'status: "spec"')
        self.assertFails("A2A.md: yaml 'status'")

    def test_signature_line_fails(self):
        self.edit("README.md", "## Notice", "<---bis3946/bis3946 is a ✨ special ✨ repository because it's `README.md`--->\n\n## Notice")
        self.assertFails("signature line")

    def test_ip_leak_fails(self):
        self.edit("interfaces/m2m.md", "## Notes", "## Notes\n- node at 192.168.1.10")
        self.assertFails("IPv4")

    def test_wrong_gate_for_a2m_fails(self):
        p = self.repo / "interfaces/interfaces.yaml"
        text = p.read_text()
        text = re.sub(r'(id: "A2M"(?:\n    .*)*?\n    gate: )"root_authority_gate"', r'\1"policy_check"', text)
        p.write_text(text)
        self.assertFails("registry:A2M: gate must be root_authority_gate")

    def test_example_msg_type_not_allowed_fails(self):
        self.edit("interfaces/a2m.md", '"msg_type": "command"', '"msg_type": "telemetry"')
        self.assertFails("A2M.md: example msg_type not allowed")

    def test_bad_interface_id_in_example_fails(self):
        self.edit("interfaces/s2s.md", '"interface": "S2S"', '"interface": "S2X"')
        self.assertFails("S2S.md: example envelope schema errors")

    def test_missing_detail_page_fails(self):
        (self.repo / "interfaces/h2h.md").unlink()
        self.assertFails("H2H: detail page missing")

    def test_identity_from_mismatch_fails(self):
        p = self.repo / "identity.json"
        d = json.loads(p.read_text())
        d["interfaces"][0]["to"] = "S"
        p.write_text(json.dumps(d, indent=2, ensure_ascii=False))
        self.assertFails("identity:A2A: from/to mismatch")

    def test_mini_yaml_matches_expected(self):
        data = vi.mini_yaml('a:\n  b: "x"\n  c: [1, "y"]\nl:\n  - id: "Q"\n    k: true\n')
        self.assertEqual(data, {"a": {"b": "x", "c": [1, "y"]}, "l": [{"id": "Q", "k": True}]})


if __name__ == "__main__":
    unittest.main()
