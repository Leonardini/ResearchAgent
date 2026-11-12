"""Concurrency test for registry_lock: N `record` calls start at once against a throwaway registry, and every one of
the N runs must be in the registry afterwards. Without the lock, concurrent load-modify-save sequences overwrite each
other and some runs go missing (the bug that lost a registration on 2026-11-12).

Usage: python3 locktest.py [N] [--script PATH]   (PATH defaults to report.py next to this file)
Exit status 0 when all N runs are present, 1 otherwise."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

n = int(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else 30
script = Path(sys.argv[sys.argv.index("--script") + 1]) if "--script" in sys.argv else Path(__file__).with_name("report.py")
with tempfile.TemporaryDirectory() as d:
    reg = Path(d) / "registry.json"
    reg.write_text(json.dumps({"families": [{
        "id": "lock", "program": "x.py", "positional_names": [], "question": "does the lock keep every run?",
        "contrast": ["k"], "measures": [{"name": "time", "from": "elapsed", "better": "lower"}]}], "runs": []}))
    procs = [subprocess.Popen([sys.executable, str(script), "--registry", str(reg), "record", "--family", "lock",
                               "--id", f"r{i}", "--param", f"k={i}", "--value", "time=1", "--source", "locktest"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True) for i in range(n)]
    errors = [p.communicate()[1].strip() for p in procs]
    failed = [e.splitlines()[-1] for p, e in zip(procs, errors) if p.returncode != 0]
    ids = {r["id"] for r in json.loads(reg.read_text())["runs"]}
    print(f"{len(ids)} of {n} runs in the registry; {len(failed)} calls failed"
          + (f" (e.g. {failed[0][:120]})" if failed else ""))
    sys.exit(0 if len(ids) == n and not failed else 1)
