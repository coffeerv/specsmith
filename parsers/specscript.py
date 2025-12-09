
from __future__ import annotations
from typing import Dict, Any, List

def parse_specscript(text: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "context": "",
        "objectives": [],
        "scope": {"in_scope": [], "out_of_scope": []},
        "metrics": [],
        "acceptance_criteria": [],
    }
    if not text:
        return out
    lines = [l.rstrip() for l in text.splitlines() if l.strip()]
    section = None
    buf: List[str] = []
    kv = {}
    def flush_section(name, buffer):
        nonlocal out
        if not name or not buffer: return
        if name in ("goals","objectives","metrics","accept","scope","feature","users","flows","constraints"):
            if name in ("goals","objectives"):
                out.setdefault("objectives", []).extend([b[2:].strip() for b in buffer if b.startswith("- ")])
            elif name == "metrics":
                out["metrics"].extend([b[2:].strip() for b in buffer if b.startswith("- ")])
            elif name == "accept":
                out["acceptance_criteria"].extend([b[2:].strip() for b in buffer if b.startswith("- ")])
            elif name == "scope":
                for b in buffer:
                    s = b.strip("- ").strip()
                    if s.lower().startswith("in:"):
                        out["scope"]["in_scope"].append(s[3:].strip())
                    elif s.lower().startswith("out:"):
                        out["scope"]["out_of_scope"].append(s[4:].strip())
        elif name == "feature":
            out["context"] += "\nFeature: " + " ".join(buffer)
        elif name in ("users","flows","constraints"):
            out["context"] += f"\n{name.capitalize()}: " + " ".join(buffer)
    i = 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("#spec"):
            i += 1
            continue
        if ":" in l and not l.startswith("- "):
            key, val = l.split(":", 1)
            key = key.strip().lower()
            val = val.strip()
            if key in ("title","type","problem","context"):
                kv[key] = val
                i += 1
                continue
        if l.endswith(":") and not l.startswith("- "):
            flush_section(section, buf)
            section = l[:-1].strip().lower()
            buf = []
        else:
            buf.append(l)
        i += 1
    flush_section(section, buf)
    if "title" in kv: out["title"] = kv["title"]
    if "type" in kv: out["type"] = kv["type"]
    if "problem" in kv: out["problem_statement"] = kv["problem"]
    if "context" in kv: out["context"] = kv["context"]
    return out
