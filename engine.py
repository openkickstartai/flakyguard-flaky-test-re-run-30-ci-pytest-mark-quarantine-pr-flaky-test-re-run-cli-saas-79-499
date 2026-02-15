"""FlakyGuard engine — flaky test detection, classification & quarantine."""
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

CAUSES = {
    "timing": ["timeout", "timed out", "sleep", "deadline", "async", "wait"],
    "resource_leak": ["memory", "oom", "connection", "file descriptor", "too many"],
    "shared_state": ["already exists", "duplicate", "conflict", "locked", "dirty"],
    "ordering": ["not found", "setup", "fixture", "depends", "missing"],
    "race_condition": ["race", "concurrent", "thread", "deadlock"],
    "timezone": ["timezone", "utc", "tz", "offset", "dst"],
    "float_precision": ["precision", "float", "decimal", "almost equal"],
}


def init_db(path="flakyguard.db"):
    """Initialize SQLite database with runs table."""
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE IF NOT EXISTS runs(
        id INTEGER PRIMARY KEY, name TEXT, status TEXT,
        duration REAL, error TEXT, run_id TEXT, ts TEXT)""")
    conn.commit()
    return conn


def ingest(db, xml_path, run_id=None):
    """Parse JUnit XML and store test results."""
    run_id = run_id or f"r-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    ts = datetime.now().isoformat()
    n = 0
    for tc in ET.parse(xml_path).iter("testcase"):
        name = f"{tc.get('classname', '')}.{tc.get('name', '')}"
        dur = float(tc.get("time", 0))
        fail_el, err_el = tc.find("failure"), tc.find("error")
        status = "fail" if fail_el is not None else ("error" if err_el is not None else "pass")
        el = fail_el if fail_el is not None else err_el
        msg = (el.get("message", "") or el.text or "") if el is not None else ""
        db.execute("INSERT INTO runs VALUES(NULL,?,?,?,?,?,?)",
                   (name, status, dur, msg, run_id, ts))
        n += 1
    db.commit()
    return n, run_id

    return n, run_id


def detect(db, min_runs=3, threshold=0.1):
    """Detect flaky tests by computing flip rate across runs."""
    rows = db.execute("""SELECT name, COUNT(*),
        SUM(CASE WHEN status!='pass' THEN 1 ELSE 0 END)
        FROM runs GROUP BY name HAVING COUNT(*)>=?""", (min_runs,)).fetchall()
    out = []
    for name, total, fails in rows:
        sts = [r[0] for r in db.execute(
            "SELECT status FROM runs WHERE name=? ORDER BY ts, id", (name,))]
        flips = sum(1 for i in range(1, len(sts)) if sts[i] != sts[i - 1])
        rate = flips / max(len(sts) - 1, 1)
        if rate >= threshold:
            out.append({"test": name, "flip_rate": round(rate, 3),
                        "runs": total, "failures": fails,
                        "root_cause": _classify(db, name)})
    return out


def _classify(db, name):
    """Classify root cause from error messages and duration variance."""
    msgs = [r[0].lower() for r in db.execute(
        "SELECT error FROM runs WHERE name=? AND status!='pass' AND error!=''",
        (name,))]
    scores = {k: sum(kw in m for m in msgs for kw in vs)
              for k, vs in CAUSES.items()}
    durs = [r[0] for r in db.execute(
        "SELECT duration FROM runs WHERE name=? AND status!='pass'", (name,))]
    if len(durs) > 1 and max(durs) > 3 * max(min(durs), 0.001):
        scores["timing"] += 2
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "non_deterministic"


def add_costs(results, db, ci_rate=0.008, rerun_min=10):
    """Calculate CI cost wasted per flaky test."""
    for r in results:
        reruns = db.execute(
            "SELECT COUNT(DISTINCT run_id) FROM runs WHERE name=? AND status!='pass'",
            (r["test"],)).fetchone()[0]
        r["cost_usd"] = round(reruns * rerun_min * ci_rate, 2)
        r["reruns"] = reruns
    return results


def quarantine_code(results):
    """Generate conftest.py code that skips quarantined tests."""
    lines = ["import pytest\n\nQUARANTINED = {\n"]
    for r in results:
        lines.append(f'    "{r["test"]}",  # flip={r["flip_rate"]:.0%} {r["root_cause"]}\n')
    lines.append("}\n\n\ndef pytest_collection_modifyitems(items):\n")
    lines.append("    for item in items:\n")
    lines.append('        fqn = f"{item.module.__name__}.{item.name}"\n')
    lines.append("        if fqn in QUARANTINED:\n")
    lines.append('            item.add_marker(pytest.mark.skip('
                 'reason="FlakyGuard quarantine"))\n')
    return "".join(lines)
