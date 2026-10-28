#!/usr/bin/env python3
"""Prototype of the proposal-triage flow.

AI reads, code decides. Mock mode (default) uses pre-extracted facts, so it runs
with no API key. Live mode reads one <letter>.txt file per proposal from
--texts-dir and calls the extraction prompt through the Anthropic API.

Usage:
  python triage.py                       # mock mode
  python triage.py --out result.json     # also write ranking JSON
  python triage.py --live --texts-dir ./texts
"""
import argparse, json, os, re
from pathlib import Path

HERE = Path(__file__).parent

# Cheap first-pass scan for text aimed at automated reviewers (rule-based).
INJECTION_PATTERNS = [
    r"automated (review|screening)",
    r"ignore (all |any )?(previous|prior|above) instructions",
    r"rank (it|this|us) (first|#?1)",
    r"full marks",
    r"pre-?approved",
    r"(highest|maximum|full) (score|marks)",
]


def load(path):
    return json.loads(Path(path).read_text())


def scan_injection(text):
    return [p for p in INJECTION_PATTERNS if re.search(p, text, re.I)]


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def missing_evidence(ext, text):
    """Rule check: every evidence quote must appear in the source text."""
    bad = []

    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "evidence" and isinstance(v, str) and v and norm(v) not in norm(text):
                    bad.append(path or "/")
                else:
                    walk(v, f"{path}/{k}")
    walk(ext)
    return bad


def extract_live(text, pid, cfg):
    import anthropic  # pip install anthropic
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    system = (HERE / "extraction_prompt.txt").read_text()
    user = (f"<assessment_date>{cfg['assessment_date']}</assessment_date>\n"
            f"<criteria>{json.dumps(cfg)}</criteria>\n"
            f"<proposal id=\"{pid}\">\n{text}\n</proposal>")
    msg = client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
        max_tokens=1500, system=system,
        messages=[{"role": "user", "content": user}])
    raw = re.sub(r"^```(?:json)?|```$", "", msg.content[0].text.strip()).strip()
    ext = json.loads(raw)
    ext["validation_errors"] = []
    hits = scan_injection(text)
    if hits:
        ext["manipulation_flag"] = {"detected": True, "description": "Rule scan matched: " + ", ".join(hits)}
    bad = missing_evidence(ext, text)
    if bad:
        ext["validation_errors"].append("Evidence quote not found in source text: " + ", ".join(bad))
    return ext


def clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def part_scores(ext, cfg, best_price):
    """Pure-code scoring. Returns 0-100 per criterion; a missing fact gives no entry."""
    w = {c["key"]: c["params"] for c in cfg["weighted"]}
    x = ext["weighted"]
    s = {}
    n = x["experience"]["qualifying_installs"]
    if n is not None:
        cap = w["experience"]["cap_installs"]
        s["experience"] = 100 * min(n, cap) / cap
    p = x["price"]["total_cad"]
    if p:
        s["price"] = 100 * best_price / p
    wk = x["timeline"]["weeks"]
    if wk is not None:
        t = w["timeline"]
        floor = t["score_at_max_weeks"]
        s["timeline"] = clamp(floor + (100 - floor) * (t["max_weeks"] - wk) / (t["max_weeks"] - t["full_marks_weeks"]))
    pw, ww = x["warranty"]["panel_years"], x["warranty"]["workmanship_years"]
    if pw is not None and ww is not None:
        c = w["warranty"]
        s["warranty"] = 50 * min(pw / c["cap_panel_years"], 1) + 50 * min(ww / c["cap_workmanship_years"], 1)
    t = x["team"]
    s["team"] = 25 * sum(bool(t[k]) for k in ("named_lead", "crew_stated", "safety_plan", "monitoring_plan"))
    return s


def gate(ext, cfg):
    """Mandatory pass/fail and hard limits. Returns a reason string if ineligible."""
    for m in cfg["mandatory"]:
        st = ext["mandatory"][m["key"]]["status"]
        if st != "met":
            return f"Mandatory criterion not met ({st}): {m['label']}."
    lim = cfg["hard_limits"]
    price = ext["weighted"]["price"]["total_cad"]
    weeks = ext["weighted"]["timeline"]["weeks"]
    if price is not None and price > lim["budget_ceiling_cad"]:
        return "Price is above the budget ceiling."
    if weeks is not None and weeks > lim["max_weeks"]:
        return "Schedule is longer than the allowed maximum."
    return None


def evaluate_all(exts, cfg):
    gates = {e["proposal_id"]: gate(e, cfg) for e in exts}
    prices = {e["proposal_id"]: e["weighted"]["price"]["total_cad"] for e in exts}
    best_price = min(p for k, p in prices.items() if gates[k] is None and p)
    weights = {c["key"]: c["weight"] for c in cfg["weighted"]}
    results = []
    for e in exts:
        pid = e["proposal_id"]
        r = {"proposal": pid, "rank": None, "status": "ranked", "score": None, "shadow_score": None, "notes": []}
        if gates[pid]:
            r.update(status="ineligible", notes=[gates[pid]])
            results.append(r)
            continue
        parts = part_scores(e, cfg, best_price)
        missing = [k for k in weights if k not in parts]
        total = None
        if not missing:
            total = round(sum(parts[k] * weights[k] / 100 for k in weights), 1)
            r["breakdown"] = {k: round(v, 1) for k, v in parts.items()}
        flags = []
        if e.get("manipulation_flag", {}).get("detected"):
            flags.append("manipulation attempt: " + e["manipulation_flag"]["description"])
        if missing:
            flags.append("missing facts: " + ", ".join(missing))
        flags += e.get("validation_errors", [])
        if flags:
            r.update(status="flagged", shadow_score=total, notes=flags)
        else:
            r["score"] = total
        results.append(r)
    ranked = sorted([r for r in results if r["status"] == "ranked"],
                    key=lambda r: (-r["score"], prices[r["proposal"]], r["proposal"]))
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    order = {"ranked": 0, "flagged": 1, "ineligible": 2}
    return sorted(results, key=lambda r: (order[r["status"]], r["rank"] or 99, r["proposal"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--texts-dir", default="texts")
    ap.add_argument("--out")
    a = ap.parse_args()
    cfg = load(HERE / "criteria.json")
    if a.live:
        exts = [extract_live(f.read_text(), f.stem, cfg) for f in sorted(Path(a.texts_dir).glob("*.txt"))]
    else:
        exts = load(HERE / "mock_extractions.json")
    results = evaluate_all(exts, cfg)
    print(f"Criteria {cfg['criteria_version']} | {cfg['category']}\n")
    for r in results:
        shadow = f" (shadow score {r['shadow_score']}, not ranked)" if r["shadow_score"] is not None else ""
        print(f"{r['proposal']}  {r['status']:<10} rank={r['rank']} score={r['score']}{shadow}")
        if r.get("breakdown"):
            print("    ", r["breakdown"])
        for n in r["notes"]:
            print("     -", n)
    if a.out:
        slim = []
        for r in results:
            reason = "; ".join(r["notes"])
            if not reason and r["status"] == "ranked":
                reason = f"Met all mandatory criteria; ranked #{r['rank']} with score {r['score']}."
            slim.append({
                "proposal": r["proposal"],
                "rank": r["rank"],
                "status": r["status"],
                "score": r["score"],
                "reason": reason
            })
        Path(a.out).write_text(json.dumps(slim, indent=2))


if __name__ == "__main__":
    main()
