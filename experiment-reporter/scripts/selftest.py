#!/usr/bin/env python3
"""selftest.py -- known-answer checks of report.py's verdicts, on synthetic runs in a temporary
directory.  Each check fails with an AssertionError naming what it expected.  Usage: selftest.py"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPORT = Path(__file__).resolve().parent / "report.py"


def run_report(d):
    out = subprocess.run([sys.executable, str(REPORT), "--registry", str(d / "registry.json")],
                         capture_output=True, text=True)
    assert out.returncode == 0, f"report.py failed: {out.stderr}"
    return out.stdout


def row(text, run_id):
    """the table row of run_id as {column header: cell}"""
    lines = text.splitlines()
    header = next(l for l in lines if l.startswith("| Run "))
    cols = [c.strip() for c in header.strip("|").split("|")]
    for line in lines:
        if line.startswith(f"| {run_id}"):
            return dict(zip(cols, (c.strip() for c in line.strip("|").split("|"))))
    raise AssertionError(f"no row for {run_id} in:\n{text}")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        fam = {"id": "f", "question": "Does the new rule shrink the tree?", "program": "sleep",
               "contrast": ["rule"], "ignore": ["arg1"], "done_regex": "^finished",
               "measures": [{"name": "nodes", "regex": r"^(\d+) nodes", "grows": True, "better": "lower"},
                            {"name": "bound", "regex": r"bound ([0-9.]+)", "better": "higher"}]}
        logB = d / "B.log"
        logB.write_text("10 nodes bound 0.5\n150 nodes bound 0.7\nfinished\n")
        logC = d / "C.log"
        logC.write_text("50 nodes bound 0.6\n")
        live = subprocess.Popen(["sleep", "60"])
        time.sleep(0.5)
        cmd = subprocess.run(["ps", "-ww", "-o", "command=", "-p", str(live.pid)],
                             capture_output=True, text=True).stdout.strip()
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        reg = {"families": [fam], "runs": [
            {"id": "A", "family": "f", "params": {"rule": "old"}, "recorded": {"nodes": 100, "bound": 0.65},
             "source": "earlier run", "started": "2026-01-01T00:00:00"},
            {"id": "B", "family": "f", "command": "sleep 1 --rule new --x 2", "log": str(logB),
             "started": "2026-01-02T00:00:00"},
            {"id": "C", "family": "f", "pid": live.pid, "command": cmd, "params": {"rule": "newer"},
             "log": str(logC), "started": now}]}
        (d / "registry.json").write_text(json.dumps(reg))
        try:
            out = run_report(d)
            # B differs from A in x as well as the contrast: a confound must be named
            assert "confounded" in out and "x" in out.split("confounded")[0].split("differ in")[-1], \
                "the x difference is not reported as a confound"
            # C is running with >= 50 nodes, so A's 100 is only the best of the finished rows
            assert row(out, "A")["nodes"].endswith("◂"), "A should lead (finished), undecided while C runs"
            assert row(out, "C")["nodes"].startswith("≥ 50"), "C's node count is a lower bound"
            assert "✓" not in row(out, "A")["nodes"], "A cannot be decided while C could finish below it"
            # bound is not a growing measure: C's 0.6 is a snapshot and decides nothing
            assert "✓" not in row(out, "A")["bound"] + row(out, "B")["bound"], "no decided best bound while C runs"
        finally:
            live.kill()
            live.wait()
        # C stopped without finishing: its 50 is still only a lower bound, so A is still undecided
        out = run_report(d)
        assert row(out, "C")["Status"].startswith("stopped") and "✓" not in row(out, "A")["nodes"], \
            "a stopped run's count is a lower bound; A must stay undecided"
        # C finishes at 120: A (100) is now the decided best, from single runs by a ratio < 10
        logC.write_text("50 nodes bound 0.6\n120 nodes bound 0.9\nfinished\n")
        out = run_report(d)
        assert row(out, "A")["nodes"] == "**100** ✓ †", f"A should be decided with the single-run caveat: {row(out, 'A')}"
        assert row(out, "C")["bound"].startswith("**0.9**"), "C has the highest bound, decided"
        # a declared minor difference: no column, no confound warning, one "Also differs" line
        reg = json.loads((d / "registry.json").read_text())
        reg["families"][0]["minor"] = ["x"]
        (d / "registry.json").write_text(json.dumps(reg))
        out = run_report(d)
        assert "confounded" not in out and "x" not in row(out, "A"), "a minor parameter got a column or a warning"
        assert "Also differs: x (A —; B 2)." in out, f"no Also-differs line for x:\n{out}"
        # triplicates: three seeds of one setting become one row with n = 3 and no caveat
        reg["families"][0]["seed_param"] = "seed"
        reg["runs"] = [r for r in reg["runs"] if r["id"] == "C"]
        for i, n in enumerate((10, 12, 11)):
            reg["runs"].append({"id": f"D{i}", "family": "f", "params": {"rule": "old", "seed": str(i)},
                                "recorded": {"nodes": n, "bound": 0.1}, "source": "test",
                                "started": "2026-01-01T00:00:00"})
        (d / "registry.json").write_text(json.dumps(reg))
        out = run_report(d)
        drow = row(out, "D0+D1+D2")
        assert drow["Status"] == "recorded, 3 runs" and drow["nodes"].startswith("**11 [10–12]**") and "†" not in drow["nodes"], \
            f"replicates should merge to median 11, n = 3, no caveat: {drow}"
        # a parameter cannot be both the contrast and minor
        bad_reg = json.loads((d / "registry.json").read_text())
        bad_reg["families"][0]["minor"] = ["rule"]
        (d / "registry.json").write_text(json.dumps(bad_reg))
        bad = subprocess.run([sys.executable, str(REPORT), "--registry", str(d / "registry.json")],
                             capture_output=True, text=True)
        assert bad.returncode != 0 and "both contrast and minor" in bad.stderr, "contrast and minor overlap must fail"
        (d / "registry.json").write_text(json.dumps(reg))
        # a broken registry hard-fails
        reg["runs"].append({"id": "E", "family": "nope", "params": {}, "recorded": {}, "source": "x"})
        (d / "registry.json").write_text(json.dumps(reg))
        bad = subprocess.run([sys.executable, str(REPORT), "--registry", str(d / "registry.json")],
                             capture_output=True, text=True)
        assert bad.returncode != 0 and "unknown family" in bad.stderr, "an unknown family must stop the report"
    print("selftest: all checks pass")


if __name__ == "__main__":
    main()
