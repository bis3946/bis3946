#!/usr/bin/env python3
"""Validate the NuN interface package of the bis3946 profile repo.

Checks that identity.json, interfaces/interfaces.yaml, interfaces/*.md
(YAML spec + example envelope), the reference implementation
tools/nun_interface.py and README.md are mutually consistent; that example
envelopes conform to interfaces/envelope.schema.json and are accepted by the
reference router; that the README Ontological Anchor equals the SHA3-256
digest recomputed here; and that no obviously non-public material (IPs, keys,
tokens, private paths) is present.

Standard library only. If the optional packages `jsonschema` / `PyYAML` are
installed they are used in addition; otherwise built-in fallbacks are used.

Usage:
    python tools/validate_interfaces.py [repo_root]           # validate
    python tools/validate_interfaces.py --anchor [repo_root]  # print anchor digest
Exit code 0 = all checks passed, 1 = at least one error.

Anchor definition (reproducible by anyone):
    sha3_256( C(identity.json) + b"\\n" + C(interfaces/interfaces.yaml) )
    where C(x) = json.dumps(parsed_x, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False).encode("utf-8")
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ACTORS = ("H", "A", "M", "S")
ALL_IDS = [f"{a}2{b}" for a in "AHMS" for b in "AHMS"]
PROTOCOL_VERSION = "1.1.0"
AUTHORITY = "bis3946"
# Hard gate requirements from Root's policy.
GATE_FOR = {
    "H2A": "human_consent", "H2M": "human_consent", "H2S": "human_consent",
    "A2H": "human_consent", "M2H": "human_consent", "S2H": "human_consent",
    "H2H": "mutual_consent",
    "A2M": "root_authority_gate", "S2M": "root_authority_gate", "S2A": "root_authority_gate",
}
SIGNATURE_LINE = re.compile(r"special\s*✨?\s*repository because", re.I)
ANCHOR_LINE = re.compile(r"Interface Anchor \(SHA3-256\):\*\*\s*`([0-9a-f]{64})`")
README_SECTIONS = [
    "## 1. Ontological Architecture (Mermaid)",
    "## 2. System Logic Mapping",
    "## 3. Interface Specifications (H/A/M/S)",
    "## 4. Entity Class Diagram",
    "## Proof & status",
    "### 🛡️ Ontological Anchor Verification (NuN Nexus)",
]

FORBIDDEN = [
    ("IPv4 address", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("API key", re.compile(r"\b(?:sk|pk|xox[abp])-[A-Za-z0-9-]{16,}")),
    ("AWS key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("long hex digest", re.compile(r"\b[0-9a-fA-F]{40,}\b")),
    ("private path", re.compile(r"(?:/home/|/Users/|/workspace/|[A-Za-z]:\\\\Users)")),
    ("local hostname", re.compile(r"\b[\w-]+\.(?:local|lan|internal)\b")),
]
SCANNED_SUFFIXES = (".md", ".json", ".yaml", ".yml", ".py", "")


# --------------------------------------------------------------------------- YAML
def _scalar(text: str):
    text = text.strip()
    if text == "":
        return None
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return [] if not inner else [_scalar(p) for p in _split_flow(inner)]
    if text[0] == '"':
        return json.loads(text)
    if text[0] == "'":
        return text[1:-1].replace("''", "'")
    if text in ("true", "false"):
        return text == "true"
    if text in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def _split_flow(s: str):
    parts, buf, q = [], "", None
    for ch in s:
        if q:
            buf += ch
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
            buf += ch
        elif ch == ",":
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    parts.append(buf)
    return [p.strip() for p in parts]


def _strip_comment(line: str) -> str:
    q = None
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


def mini_yaml(text: str):
    """Parse the block-style YAML subset used in this repo (maps, lists of maps,
    flow lists, quoted/plain scalars). Not a general YAML parser."""
    lines = []
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if line.strip():
            lines.append((len(line) - len(line.lstrip(" ")), line.strip()))
    pos = 0

    def parse_block(indent):
        if pos < len(lines) and lines[pos][1].startswith("- "):
            return parse_list(indent)
        return parse_map(indent)

    def parse_map(indent, first=None):
        nonlocal pos
        result = {}
        if first is not None:
            result[first[0]] = first[1]
        while pos < len(lines):
            ind, content = lines[pos]
            if ind < indent or content.startswith("- "):
                break
            if ind > indent:
                raise ValueError(f"unexpected indent: {content!r}")
            key, sep, rest = content.partition(":")
            if not sep:
                raise ValueError(f"expected key: {content!r}")
            pos += 1
            key = key.strip().strip('"')
            if rest.strip() == "":
                if pos < len(lines) and lines[pos][0] > ind:
                    result[key] = parse_block(lines[pos][0])
                elif pos < len(lines) and lines[pos][0] == ind and lines[pos][1].startswith("- "):
                    result[key] = parse_list(ind)
                else:
                    result[key] = None
            else:
                result[key] = _scalar(rest)
        return result

    def parse_list(indent):
        nonlocal pos
        items = []
        while pos < len(lines):
            ind, content = lines[pos]
            if ind != indent or not content.startswith("- "):
                break
            body = content[2:].strip()
            pos += 1
            key, sep, rest = body.partition(":")
            if sep and not body.startswith(("\"", "'", "[")):
                child_indent = indent + 2
                if rest.strip() == "" and pos < len(lines) and lines[pos][0] > child_indent:
                    val = parse_block(lines[pos][0])
                else:
                    val = _scalar(rest)
                items.append(parse_map(child_indent, (key.strip(), val)))
            else:
                items.append(_scalar(body))
        return items

    data = parse_block(lines[0][0] if lines else 0)
    if pos != len(lines):
        raise ValueError(f"could not parse line: {lines[pos][1]!r}")
    return data


def load_yaml(text: str):
    try:
        import yaml  # type: ignore
    except ImportError:
        return mini_yaml(text)
    return yaml.safe_load(text)


# --------------------------------------------------------------------------- JSON Schema
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool,
          "integer": int, "number": (int, float), "null": type(None)}


def mini_validate(instance, schema, path="$"):
    """Validate against the JSON Schema subset used by envelope.schema.json."""
    errs = []
    t = schema.get("type")
    if t:
        ok = isinstance(instance, _TYPES[t]) and not (t in ("integer", "number") and isinstance(instance, bool))
        if not ok:
            return [f"{path}: expected {t}"]
    if "const" in schema and instance != schema["const"]:
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: {instance!r} not in enum")
    if isinstance(instance, str):
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errs.append(f"{path}: {instance!r} does not match {schema['pattern']}")
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errs.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errs.append(f"{path}: longer than {schema['maxLength']}")
        if schema.get("format") == "date-time":
            try:
                datetime.fromisoformat(instance.replace("Z", "+00:00"))
            except ValueError:
                errs.append(f"{path}: invalid date-time")
    if isinstance(instance, dict):
        props = schema.get("properties", {})
        errs += [f"{path}: missing required '{k}'" for k in schema.get("required", []) if k not in instance]
        for k, v in instance.items():
            if k in props:
                errs += mini_validate(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected property '{k}'")
    return errs


def schema_errors(instance, schema):
    errs = mini_validate(instance, schema)
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return errs
    v = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    return errs + [f"jsonschema: {e.message}" for e in v.iter_errors(instance)]


# --------------------------------------------------------------------------- helpers
def fenced_blocks(md: str, lang: str):
    return re.findall(rf"```{lang}\n(.*?)```", md, flags=re.S)


def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_anchor(root: Path) -> str:
    """SHA3-256 over canonical identity.json + newline + canonical interfaces.yaml."""
    ident = json.loads((root / "identity.json").read_text(encoding="utf-8"))
    reg = load_yaml((root / "interfaces/interfaces.yaml").read_text(encoding="utf-8"))
    return hashlib.sha3_256(canonical_json(ident) + b"\n" + canonical_json(reg)).hexdigest()


def load_reference(root: Path):
    path = root / "tools" / "nun_interface.py"
    spec = importlib.util.spec_from_file_location(f"nun_interface_{abs(hash(str(root)))}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses need the module registered
    spec.loader.exec_module(mod)
    return mod


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.checks = 0

    def check(self, cond, msg: str) -> bool:
        self.checks += 1
        if not cond:
            self.errors.append(msg)
        return bool(cond)


def validate(root: Path) -> Report:
    r = Report()
    for rel in ["README.md", "NOTICE", "identity.json", "interfaces/interfaces.yaml",
                "interfaces/envelope.schema.json", "tools/nun_interface.py", ".github/workflows/validate.yml"]:
        r.check((root / rel).is_file(), f"missing file: {rel}")
    if r.errors:
        return r

    # schema -----------------------------------------------------------------
    schema = json.loads((root / "interfaces/envelope.schema.json").read_text(encoding="utf-8"))
    r.check(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema",
            "schema: $schema must be draft 2020-12")
    r.check(schema.get("properties", {}).get("interface", {}).get("pattern") == "^[AHMS]2[AHMS]$",
            "schema: interface pattern must be ^[AHMS]2[AHMS]$")
    r.check("signature" not in schema.get("required", []), "schema: signature must be optional")
    try:
        import jsonschema  # type: ignore
        jsonschema.Draft202012Validator.check_schema(schema)
    except ImportError:
        pass
    except Exception as e:  # noqa: BLE001
        r.check(False, f"schema: invalid JSON Schema: {e}")

    # registry ---------------------------------------------------------------
    reg = load_yaml((root / "interfaces/interfaces.yaml").read_text(encoding="utf-8"))
    meta = reg.get("registry", {})
    r.check(meta.get("authority") == AUTHORITY, "registry: authority must be bis3946")
    r.check(meta.get("protocol_version") == PROTOCOL_VERSION, "registry: protocol_version mismatch")
    r.check(meta.get("envelope_schema") == "interfaces/envelope.schema.json", "registry: envelope_schema link")
    gates = reg.get("gates", {}) or {}
    r.check(sorted(gates) == sorted(schema["properties"]["gate"]["properties"]["type"]["enum"]),
            "registry: gates differ from schema gate enum")
    reg_list = reg.get("interfaces", []) or []
    reg_ifaces = {i["id"]: i for i in reg_list}
    r.check(len(reg_list) == 16, "registry: must list exactly 16 interfaces")
    r.check(sorted(reg_ifaces) == sorted(ALL_IDS), "registry: ids must be the full 16-scheme set")

    # identity ---------------------------------------------------------------
    ident = json.loads((root / "identity.json").read_text(encoding="utf-8"))
    hdr = ident.get("header", {})
    r.check(hdr.get("authority") == AUTHORITY, "identity: authority must be bis3946")
    r.check(hdr.get("protocol_version") == PROTOCOL_VERSION, "identity: protocol_version mismatch")
    r.check(ident.get("envelope_schema") == "interfaces/envelope.schema.json", "identity: envelope_schema link")
    r.check(ident.get("interface_registry") == "interfaces/interfaces.yaml", "identity: interface_registry link")
    r.check(sorted(ident.get("actors", {})) == sorted(ACTORS), "identity: actors must be H/A/M/S")
    id_list = ident.get("interfaces", []) or []
    id_ifaces = {i["id"]: i for i in id_list}
    r.check(len(id_list) == 16, "identity: must list exactly 16 interfaces")
    r.check(sorted(id_ifaces) == sorted(ALL_IDS), "identity: ids must be the full 16-scheme set")

    # reference implementation -------------------------------------------------
    try:
        ni = load_reference(root)
    except Exception as e:  # noqa: BLE001
        r.check(False, f"reference: cannot import tools/nun_interface.py: {e}")
        ni = None
    if ni is not None:
        r.check(ni.PROTOCOL_VERSION == PROTOCOL_VERSION and ni.AUTHORITY == AUTHORITY,
                "reference: protocol_version / authority mismatch")
        r.check(sorted(ni.REGISTRY) == sorted(ALL_IDS), "reference: REGISTRY must hold the 16 schemes")
        r.check(sorted(ni.HANDLERS) == sorted(ALL_IDS), "reference: HANDLERS must cover the 16 schemes")
        r.check(list(ni.MSG_TYPES) == schema["properties"]["msg_type"]["enum"], "reference: MSG_TYPES != schema enum")
        r.check(sorted(ni.GATES) == sorted(gates), "reference: GATES != registry gates")

    readme = (root / "README.md").read_text(encoding="utf-8")
    r.check(not SIGNATURE_LINE.search(readme), "README: GitHub template signature line must be absent")
    for sec in README_SECTIONS:
        r.check(sec in readme, f"README: section missing: {sec}")
    for mod_id in ("MOD-ONTOLOGY-MAPPING-001", "MOD-INTERFACE-MATRIX-016"):
        r.check(mod_id in readme, f"README: module id {mod_id} missing")
    r.check("[✨] ≡ `@bis3946`" in readme, "README: ✨ ≡ @bis3946 binding statement missing")

    # README interface_stack yaml
    stack = None
    for block in fenced_blocks(readme, "yaml"):
        if block.lstrip().startswith("interface_stack:"):
            stack = load_yaml(block).get("interface_stack", {})
    if r.check(stack is not None, "README: interface_stack yaml block missing"):
        r.check(sorted((stack.get("actors") or {})) == sorted(ACTORS), "README: interface_stack actors")
        r.check(sorted((stack.get("interfaces") or {})) == sorted(ALL_IDS), "README: interface_stack must list 16")

    # anchor
    anchor = compute_anchor(root)
    m = ANCHOR_LINE.search(readme)
    r.check(m is not None and m.group(1) == anchor,
            f"README: Ontological Anchor digest must equal recomputed {anchor}")

    for sid in ALL_IDS:
        ri, ii = reg_ifaces.get(sid), id_ifaces.get(sid)
        if not (ri and ii):
            continue
        for src, item in (("registry", ri), ("identity", ii)):
            r.check(item.get("from") == sid[0] and item.get("to") == sid[2], f"{src}:{sid}: from/to mismatch")
            r.check(item.get("status") == "live", f"{src}:{sid}: status must be live")
            r.check(item.get("detail") == f"interfaces/{sid.lower()}.md", f"{src}:{sid}: detail path")
        for key in ("purpose", "gate", "detail"):
            r.check(ri.get(key) == ii.get(key), f"{sid}: '{key}' differs between registry and identity")
        r.check(ri.get("gate") in gates, f"registry:{sid}: unknown gate {ri.get('gate')!r}")
        if sid in GATE_FOR:
            r.check(ri.get("gate") == GATE_FOR[sid], f"registry:{sid}: gate must be {GATE_FOR[sid]}")
        types = ri.get("message_types") or []
        r.check(bool(types) and set(types) <= set(schema["properties"]["msg_type"]["enum"]),
                f"registry:{sid}: message_types must be non-empty and within schema enum")
        if ni is not None and sid in ni.REGISTRY:
            spec = ni.REGISTRY[sid]
            r.check((spec.purpose, spec.gate, list(spec.message_types), spec.status) ==
                    (ri.get("purpose"), ri.get("gate"), types, ri.get("status")),
                    f"reference:{sid}: REGISTRY entry differs from interfaces.yaml")
        if stack:
            r.check((stack.get("interfaces") or {}).get(sid) == [sid[0], sid[2], ri.get("gate"), "live"],
                    f"README:{sid}: interface_stack entry must be [from, to, gate, live]")

        row = re.search(rf"^\|\s*`{sid}`\s*\|.*$", readme, flags=re.M)
        r.check(bool(row) and "live" in row.group(0) and f"./interfaces/{sid.lower()}.md" in row.group(0),
                f"README:{sid}: table row must exist, be live and link to detail")
        r.check(f"{sid[0]} -->|{sid}| {sid[2]}" in readme, f"README:{sid}: topology edge missing")
        r.check(f"G{sid}" in readme, f"README:{sid}: architecture gateway node missing")

        p = root / "interfaces" / f"{sid.lower()}.md"
        if not r.check(p.is_file(), f"{sid}: detail page missing"):
            continue
        md = p.read_text(encoding="utf-8")
        r.check(f"OFFICIAL {sid} INTERFACE" in md, f"{sid}.md: title")
        r.check("Status: **live**" in md, f"{sid}.md: status banner must be live")
        r.check(len(fenced_blocks(md, "mermaid")) >= 1, f"{sid}.md: mermaid flow missing")
        yb, jb = fenced_blocks(md, "yaml"), fenced_blocks(md, "json")
        if not r.check(len(yb) == 1 and len(jb) == 1, f"{sid}.md: need exactly one yaml and one json block"):
            continue
        spec_md = (load_yaml(yb[0]) or {}).get("interface", {})
        expect = {"id": sid, "from": sid[0], "to": sid[2], "authority": AUTHORITY,
                  "protocol_version": PROTOCOL_VERSION, "status": "live",
                  "envelope": "./envelope.schema.json", "gate": ri.get("gate")}
        for k, v in expect.items():
            r.check(spec_md.get(k) == v, f"{sid}.md: yaml '{k}' should be {v!r}, got {spec_md.get(k)!r}")
        r.check(spec_md.get("message_types") == types, f"{sid}.md: yaml message_types differ from registry")

        env = json.loads(jb[0])
        errs = schema_errors(env, schema)
        r.check(not errs, f"{sid}.md: example envelope schema errors: {errs}")
        r.check(env.get("interface") == sid, f"{sid}.md: example interface must be {sid}")
        r.check(env.get("from", {}).get("actor") == sid[0], f"{sid}.md: example from.actor")
        r.check(env.get("to", {}).get("actor") == sid[2], f"{sid}.md: example to.actor")
        r.check(env.get("msg_type") in types, f"{sid}.md: example msg_type not allowed for {sid}")
        gate = env.get("gate", {})
        r.check(gate.get("type") == ri.get("gate"), f"{sid}.md: example gate type mismatch")
        if gate.get("type") == "human_consent":
            r.check(str(gate.get("granted_by", "")).startswith("human:") and gate.get("scope"),
                    f"{sid}.md: human_consent needs granted_by human:* and scope")
        if gate.get("type") == "root_authority_gate":
            r.check(gate.get("granted_by") == AUTHORITY and gate.get("scope"),
                    f"{sid}.md: root_authority_gate needs granted_by bis3946 and scope")
        r.check(env.get("signature") in (None, "UNSIGNED-EXAMPLE"), f"{sid}.md: signature must be a placeholder")
        if ni is not None:
            r.check(not ni.validate_envelope(env), f"{sid}.md: reference validate_envelope rejects example")
            rc = ni.Router().route(env)
            r.check(rc.status == "accepted", f"{sid}.md: reference router rejects example: {rc.reason}")
            r.check(env == ni.example_envelope(sid).to_dict(), f"{sid}.md: example differs from reference example")

    for p in (root / "interfaces").glob("*.md"):
        r.check(p.stem.upper() in ALL_IDS, f"unexpected interface page: {p.name}")

    # public-safety scan --------------------------------------------------------
    for p in sorted(root.rglob("*")):
        if not p.is_file() or ".git" in p.parts or "__pycache__" in p.parts or p.suffix not in SCANNED_SUFFIXES:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if p.name == "README.md" and p.parent == root:
            text = text.replace(anchor, "")  # the published, verifiable anchor is allowed
        for label, rx in FORBIDDEN:
            if p.suffix == ".py" and label in ("IPv4 address", "private key block", "GitHub token", "API key",
                                               "private path"):
                continue  # detection regexes live in source files
            hit = rx.search(text)
            r.check(hit is None, f"public-safety: {label} in {p.relative_to(root)}: {hit.group(0) if hit else ''}")
    return r


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    want_anchor = "--anchor" in argv
    argv = [a for a in argv if a != "--anchor"]
    root = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent
    if want_anchor:
        print(compute_anchor(root))
        return 0
    r = validate(root)
    for e in r.errors:
        print(f"ERROR: {e}")
    print(f"{'PASS' if not r.errors else 'FAIL'}: {r.checks - len(r.errors)}/{r.checks} checks passed")
    print(f"anchor sha3-256: {compute_anchor(root)}")
    return 0 if not r.errors else 1


if __name__ == "__main__":
    sys.exit(main())
