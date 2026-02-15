"""Tests for FlakyGuard engine — flaky detection, classification & cost."""
import os
import tempfile

import pytest

import engine

JUNIT_PASS = """<?xml version="1.0"?>
<testsuite tests="2">
  <testcase classname="test_math" name="test_add" time="0.01"/>
  <testcase classname="test_math" name="test_sub" time="0.02"/>
</testsuite>"""

JUNIT_FAIL = """<?xml version="1.0"?>
<testsuite tests="2">
  <testcase classname="test_math" name="test_add" time="0.5">
    <failure message="timeout waiting for response">AssertionError</failure>
  </testcase>
  <testcase classname="test_math" name="test_sub" time="0.02"/>
</testsuite>"""


def _tmpxml(content):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False)
    f.write(content)
    f.close()
    return f.name


@pytest.fixture()
def db(tmp_path):
    return engine.init_db(str(tmp_path / "test.db"))


def test_ingest_parses_junit_xml(db):
    path = _tmpxml(JUNIT_PASS)
    n, rid = engine.ingest(db, path, "run-1")
    os.unlink(path)
    assert n == 2
    rows = db.execute("SELECT * FROM runs").fetchall()
    assert len(rows) == 2
    assert all(r[2] == "pass" for r in rows)


def test_detect_finds_flaky_by_flip_rate(db):
    p, f = _tmpxml(JUNIT_PASS), _tmpxml(JUNIT_FAIL)
    for i, xml in enumerate([p, f, p, f, p]):
        engine.ingest(db, xml, f"run-{i}")
    results = engine.detect(db, min_runs=3, threshold=0.1)
    os.unlink(p)
    os.unlink(f)
    flaky = [r for r in results if r["test"] == "test_math.test_add"]
    assert len(flaky) == 1
    assert flaky[0]["flip_rate"] >= 0.5
    stable = [r for r in results if r["test"] == "test_math.test_sub"]
    assert len(stable) == 0


def test_root_cause_classifies_timing(db):
    f = _tmpxml(JUNIT_FAIL)
    p = _tmpxml(JUNIT_PASS)
    for i in range(4):
        engine.ingest(db, f, f"fail-{i}")
    engine.ingest(db, p, "pass-0")
    results = engine.detect(db, min_runs=3, threshold=0.1)
    os.unlink(f)
    os.unlink(p)
    flaky = [r for r in results if "test_add" in r["test"]]
    assert len(flaky) == 1
    assert flaky[0]["root_cause"] == "timing"


def test_cost_attribution_calculates_dollars(db):
    p, f = _tmpxml(JUNIT_PASS), _tmpxml(JUNIT_FAIL)
    for i, xml in enumerate([p, f, p, f]):
        engine.ingest(db, xml, f"run-{i}")
    results = engine.detect(db, min_runs=3, threshold=0.1)
    results = engine.add_costs(results, db, ci_rate=0.01, rerun_min=10)
    os.unlink(p)
    os.unlink(f)
    assert len(results) >= 1
    assert all(r["cost_usd"] > 0 for r in results)
    assert all(r["reruns"] >= 1 for r in results)


def test_quarantine_generates_valid_python(db):
    p, f = _tmpxml(JUNIT_PASS), _tmpxml(JUNIT_FAIL)
    for i, xml in enumerate([p, f, p, f, p]):
        engine.ingest(db, xml, f"run-{i}")
    results = engine.detect(db, min_runs=3, threshold=0.1)
    code = engine.quarantine_code(results)
    os.unlink(p)
    os.unlink(f)
    assert "QUARANTINED" in code
    assert "pytest_collection_modifyitems" in code
    compile(code, "<quarantine>", "exec")
