#!/usr/bin/env python3
"""report.py -- tables of running experiments against the settings they are compared with.

Standard library only.  The registry (a JSON file, by default experiments/registry.json found
upwards from the current directory) holds FAMILIES and RUNS:

  * a family is one question ("do 2x2 minors shrink the tree?"): the measures that answer it,
    which direction is better for each, and which parameters are the contrast;
  * a run is one setting of that question: a live process (registered with its pid and log),
    or a result recorded earlier and not rerun.

Commands
  report.py [--registry P]                     print the report (Markdown) on stdout; a family
                                               whose runs have all ended is shown once in that
                                               final state, then retired
  report.py --all | --family ID ... | --since today|YYYY-MM-DD[THH:MM]
                                               also show retired and closed families: every one,
                                               the ones named, or those with a run active since
  report.py register --family F --id ID --pid PID --log LOG [--note T]
                                               record a launched process (command and start
                                               time are read from ps)
  report.py record --family F --id ID --param k=v ... --value measure=v ... --source T
                                               record an earlier result that is not rerun
  report.py check                              validate the registry and stop

Winner logic.  Every value is an interval: a finished value is exact; a running (or stopped)
value of a measure that only grows (elapsed time, nodes, peak memory) is a lower bound; a
snapshot of a running run (current RSS) bounds nothing.  A row is the decided best when its
interval beats every other row's interval; otherwise the best value so far is only "leading".
See references/registry.md for the format.
"""
import argparse
import hashlib
import json
import math
import os
import re
import shlex
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

STATE_NAME = ".last_report.json"
DEFAULT_CATEGORY_RATIO = 10.0   # a single-run ratio below this is not a measurement (triplicate rule)
DEFAULT_STALL_MINUTES = 30.0
TAIL_BLOCK = 1 << 20


class RegistryError(Exception):
    pass


def fail(msg):
    raise RegistryError(msg)


# ---------------------------------------------------------------- registry

def find_registry(start):
    for d in [start, *start.parents]:
        p = d / "experiments" / "registry.json"
        if p.exists():
            return p
    fail(f"no experiments/registry.json in {start} or any parent; pass --registry or create one "
         f"(see references/registry.md)")


def load(path):
    try:
        reg = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        fail(f"{path} is not valid JSON: {e}")
    reg.setdefault("families", [])
    reg.setdefault("runs", [])
    validate(reg)
    return reg


def save(path, reg):
    validate(reg)
    path.write_text(json.dumps(reg, indent=2) + "\n")


def validate(reg):
    fams = {}
    for f in reg["families"]:
        for k in ("id", "question", "measures"):
            if k not in f:
                fail(f"family {f.get('id', '?')}: missing '{k}'")
        if f["id"] in fams:
            fail(f"family id {f['id']} appears twice")
        fams[f["id"]] = f
        names = set()
        for m in f["measures"]:
            if "name" not in m or m.get("better") not in ("lower", "higher"):
                fail(f"family {f['id']}: every measure needs a name and better = lower|higher: {m}")
            if m["name"] in names:
                fail(f"family {f['id']}: measure {m['name']} appears twice")
            names.add(m["name"])
            sources = [k for k in ("regex", "from") if k in m]
            if len(sources) != 1:
                fail(f"family {f['id']}, measure {m['name']}: give exactly one of regex / from")
            if "from" in m and m["from"] not in ("elapsed", "rss"):
                fail(f"family {f['id']}, measure {m['name']}: from must be elapsed or rss")
            if "regex" in m:
                try:
                    rx = re.compile(m["regex"], re.M)
                except re.error as e:
                    fail(f"family {f['id']}, measure {m['name']}: bad regex: {e}")
                if rx.groups < 1:
                    fail(f"family {f['id']}, measure {m['name']}: the regex needs one capture group")
        for k in ("contrast", "ignore", "minor"):
            if not isinstance(f.get(k, []), list):
                fail(f"family {f['id']}: {k} must be a list")
        both = set(f.get("contrast", [])) & set(f.get("minor", []))
        if both:
            fail(f"family {f['id']}: {sorted(both)} listed as both contrast and minor")
        if "done_regex" in f:
            re.compile(f["done_regex"], re.M)
    ids = set()
    for r in reg["runs"]:
        if "id" not in r or "family" not in r:
            fail(f"run without id or family: {r}")
        if r["id"] in ids:
            fail(f"run id {r['id']} appears twice")
        ids.add(r["id"])
        if r["family"] not in fams:
            fail(f"run {r['id']}: unknown family {r['family']}")
        if "recorded" in r:
            unknown = set(r["recorded"]) - {m["name"] for m in fams[r["family"]]["measures"]}
            if unknown:
                fail(f"run {r['id']}: recorded values for unknown measures {sorted(unknown)}")
        else:
            for k in ("command", "log", "started"):
                if k not in r:
                    fail(f"run {r['id']}: a process run needs '{k}' (use register)")


# ---------------------------------------------------------------- processes

def parse_etime(s):
    """ps etime [[dd-]hh:]mm:ss -> seconds"""
    days, _, rest = s.strip().rpartition("-")
    parts = [int(x) for x in rest.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, sec = parts
    return (int(days) if days else 0) * 86400 + h * 3600 + m * 60 + sec


def ps_table():
    out = subprocess.run(["ps", "-ww", "-Ao", "pid=,etime=,rss=,%cpu=,command="],
                         capture_output=True, text=True, check=True).stdout
    procs = {}
    for line in out.splitlines():
        f = line.split(None, 4)
        if len(f) < 5:
            continue
        procs[int(f[0])] = {"etime": parse_etime(f[1]), "rss_kb": int(f[2]),
                            "cpu": float(f[3]), "command": f[4]}
    return procs


# ---------------------------------------------------------------- logs

def last_match(path, rx):
    """last match of rx in the file: search the last block, doubling it until the whole file"""
    size = path.stat().st_size
    block = TAIL_BLOCK
    with open(path, "rb") as fh:
        while True:
            start = max(0, size - block)
            fh.seek(start)
            text = fh.read().decode("utf-8", "replace")
            if start > 0:                       # drop the partial first line
                text = text[text.find("\n") + 1:]
            ms = list(rx.finditer(text))
            if ms:
                return ms[-1]
            if start == 0:
                return None
            block *= 2


def to_number(s):
    s = s.replace(",", "").replace("_", "")
    v = float(s)
    return int(v) if v.is_integer() and "." not in s and "e" not in s.lower() else v


# ---------------------------------------------------------------- parameters

def params_of(run, fam):
    params = {} if "recorded" in run else parse_command(run, fam)
    params.update(run.get("params", {}))     # explicit params override the parsed ones
    for k, v in fam.get("defaults", {}).items():
        params.setdefault(k, v)              # the value a parameter takes when it is not given
    for k in fam.get("ignore", []):
        params.pop(k, None)
    if fam.get("seed_param"):
        params.pop(fam["seed_param"], None)
    return {k: str(v) for k, v in params.items()}


def parse_command(run, fam):
    """--key value, --key=value, --flag (-> on) and named positionals after the program"""
    toks = shlex.split(run["command"])
    prog = fam.get("program")
    if prog:
        idx = [i for i, t in enumerate(toks) if t.endswith(prog)]
        if not idx:
            fail(f"run {run['id']}: program {prog} not in its command")
        toks = toks[idx[0] + 1:]
    else:
        toks = toks[1:]
    names = fam.get("positional_names", [])
    params, pos, i = {}, 0, 0
    while i < len(toks):
        t = toks[i]
        if t in (">", "2>", ">>", "2>>", "|", "&"):
            break
        if t.startswith("--"):
            key, eq, val = t[2:].partition("=")
            if eq:
                params[key] = val
            elif i + 1 < len(toks) and not toks[i + 1].startswith("--") and toks[i + 1] not in (">", "2>"):
                params[key] = toks[i + 1]
                i += 1
            else:
                params[key] = "on"
        else:
            params[names[pos] if pos < len(names) else f"arg{pos + 1}"] = t
            pos += 1
        i += 1
    return params


# ---------------------------------------------------------------- measuring

def measure_run(run, fam, procs, now):
    """status and one interval per measure: {name: (shown, lo, hi, kind)}"""
    res = {"id": run["id"], "values": {}, "notes": []}
    if "recorded" in run:
        res["status"] = "recorded"
        for m in fam["measures"]:
            v = run["recorded"].get(m["name"])
            res["values"][m["name"]] = None if v is None else (v, v, v, "exact")
        return res
    log = Path(run["log"])
    if not log.exists():
        fail(f"run {run['id']}: its log {log} is missing (it existed when the run was registered)")
    p = procs.get(run.get("pid"))
    alive = p is not None and p["command"] == run["command"]
    done = False
    if not alive and fam.get("done_regex"):
        done = last_match(log, re.compile(fam["done_regex"], re.M)) is not None
    res["status"] = "running" if alive else ("done" if done else "stopped")
    started = datetime.fromisoformat(run["started"]).timestamp()
    mtime = log.stat().st_mtime
    res["silent_min"] = (now - mtime) / 60 if alive else None
    for m in fam["measures"]:
        grows = m.get("grows", m.get("from") == "elapsed")
        if m.get("from") == "elapsed":
            if alive:
                v, kind = p["etime"], "partial"
            else:
                v, kind = mtime - started, ("approx" if done else "partial")
        elif m.get("from") == "rss":
            if not alive:
                res["values"][m["name"]] = None
                continue
            v, kind = p["rss_kb"] / 2**20, "snapshot"
        else:
            mt = last_match(log, re.compile(m["regex"], re.M))
            if mt is None:
                res["values"][m["name"]] = None
                continue
            v = to_number(mt.group(1)) * m.get("scale", 1)
            kind = "exact" if done else ("partial" if grows else ("snapshot" if alive else "last"))
        if kind in ("exact", "approx"):
            res["values"][m["name"]] = (v, v, v, kind)
        elif kind == "partial" and grows:
            res["values"][m["name"]] = (v, v, math.inf, kind)
        else:
            res["values"][m["name"]] = (v, -math.inf, math.inf, kind)
    if alive:
        res["cpu"], res["rss_gb"] = p["cpu"], p["rss_kb"] / 2**20
    return res


def merge_replicates(rows):
    """rows with one setting (seed aside) -> one row: median, range, n"""
    if len(rows) == 1:
        rows[0]["n"] = 1
        return rows[0]
    out = {"id": "+".join(r["id"] for r in rows), "n": len(rows), "values": {}, "notes": [],
           "status": next(st for st in ("running", "stopped", "done", "recorded")
                          if any(r["status"] == st for r in rows)),
           "silent_min": None}
    for name in rows[0]["values"]:
        vals = [r["values"][name] for r in rows]
        if any(v is None for v in vals):
            out["values"][name] = None
            continue
        exact = all(v[3] in ("exact", "approx") for v in vals)
        med = statistics.median(v[0] for v in vals)
        lo = statistics.median(v[1] for v in vals)
        hi = statistics.median(v[2] for v in vals) if exact else math.inf
        out["values"][name] = (med, lo, hi, "exact" if exact else "partial")
        out.setdefault("range", {})[name] = (min(v[0] for v in vals), max(v[0] for v in vals))
    return out


def judge(rows, m):
    """per row: 'best' (decided), 'lead' (best so far, undecided) or ''"""
    name, lower = m["name"], m["better"] == "lower"
    have = [(i, r["values"][name]) for i, r in enumerate(rows) if r["values"].get(name)]
    marks = [""] * len(rows)
    if len(have) < 2:
        return marks, None
    for i, (v, lo, hi, _) in have:
        others = [w for j, w in have if j != i]
        if lower and all(hi <= w[1] for w in others) or not lower and all(lo >= w[2] for w in others):
            marks[i] = "best"
    if not any(marks):
        # "leading" only means something for a finished value that an unfinished row could
        # still beat; an unfinished value that is merely smaller (a younger run) leads nothing
        final = [(v[0], i) for i, v in have if v[3] in ("exact", "approx")]
        if final:
            target = min(final)[0] if lower else max(final)[0]
            if all((v[0] >= target) if lower else (v[0] <= target) for _, v in have if v[3] in ("exact", "approx")):
                for v, i in final:
                    if v == target:
                        marks[i] = "lead"
    # a decided winner from fewer than 3 runs a side, by a ratio below the category threshold
    caveat = None
    winners = [i for i, k in enumerate(marks) if k == "best"]
    if winners:
        w = rows[winners[0]]["values"][name][0]
        rest = [v[0] for j, v in have if j not in winners]
        if rest and w not in (0, None):
            nearest = min(rest) if lower else max(rest)
            ratio = nearest / w if lower else w / nearest if nearest else math.inf
            runs = min(rows[i].get("n", 1) for i, _ in have)
            caveat = (ratio, runs)
    return marks, caveat


# ---------------------------------------------------------------- formatting

def fmt_value(v, m):
    if v is None:
        return "—"
    x = v[0]
    if m.get("from") == "elapsed":
        s = f"{x:.0f} s" if x < 120 else f"{x / 60:.0f} min" if x < 7200 else f"{x / 3600:.1f} h"
    elif isinstance(x, int) or float(x).is_integer() and abs(x) >= 1:
        s = f"{int(x):,}"
    else:
        s = f"{x:.3g}"
    unit = m.get("unit")
    if unit and m.get("from") != "elapsed":
        s += f" {unit}"
    prefix = {"partial": "≥ ", "snapshot": "now ", "last": "last ", "approx": "~"}.get(v[3], "")
    return prefix + s


def fmt_status(r):
    s = r["status"]
    if r.get("silent_min") is not None and r["silent_min"] >= r.get("stall", DEFAULT_STALL_MINUTES):
        s += f", **silent {r['silent_min']:.0f} min**"
    if r.get("n", 1) > 1:
        s += f", {r['n']} runs"
    return s


def family_report(fam, runs, procs, now, state, new_state):
    measured = []
    for run in runs:
        r = measure_run(run, fam, procs, now)
        r["params"] = params_of(run, fam)
        r["role"] = run.get("role", "")
        r["started"] = run.get("started", "")
        r["stall"] = fam.get("stall_minutes", DEFAULT_STALL_MINUTES)
        measured.append(r)
    # replicates: identical parameters (the seed is already dropped) form one row
    groups = {}
    for r in measured:
        groups.setdefault(json.dumps(r["params"], sort_keys=True), []).append(r)
    rows = []
    for g in groups.values():
        merged = merge_replicates(g)
        merged["params"], merged["role"] = g[0]["params"], g[0]["role"]
        merged["started"], merged["stall"] = min(x["started"] for x in g), g[0]["stall"]
        rows.append(merged)
    ref_id = fam.get("reference")
    rows.sort(key=lambda r: (r["id"] != ref_id, r["started"] or ""))
    ref = rows[0]
    keys = sorted({k for r in rows for k in r["params"]})
    varying = [k for k in keys if len({r["params"].get(k) for r in rows}) > 1]
    fixed = [k for k in keys if k not in varying]
    contrast = fam.get("contrast") or varying
    missing = [k for k in contrast if k not in keys]
    if missing:
        fail(f"family {fam['id']}: contrast parameters {missing} appear in no run")
    # declared minor differences go on one line under the table; undeclared ones are confounds
    minor = [k for k in varying if k in fam.get("minor", []) and k not in contrast]
    confounds = [k for k in varying if k not in contrast and k not in minor]
    cols = list(dict.fromkeys(contrast + confounds))

    out = [f"### {fam['question']}", ""]
    if fixed:
        out.append("Fixed: " + ", ".join(f"{k} {ref['params'][k]}" if ref["params"][k] != "on" else k
                                         for k in fixed))
    out.append("Contrast: " + ", ".join(f"**{k}**" for k in contrast)
               + f" (reference row: {ref['id']})")
    if confounds:
        out.append(f"⚠ Rows also differ in {', '.join(confounds)}, which is not the declared "
                   f"contrast: the comparison is confounded.")
    out.append("")
    hdr = ["Run", "Status"] + cols + [m["name"] for m in fam["measures"]]
    out.append("| " + " | ".join(hdr) + " |")
    out.append("|" + "---|" * len(hdr))
    judged = {m["name"]: judge(rows, m) for m in fam["measures"]}
    caveats = []
    for i, r in enumerate(rows):
        label = r["id"] + (" (ref)" if r is ref else "")
        cells = [label, fmt_status(r)]
        for k in cols:
            v = r["params"].get(k, "—")
            cells.append(f"**{v}**" if r is not ref and v != ref["params"].get(k, "—") else v)
        for m in fam["measures"]:
            s = fmt_value(r["values"].get(m["name"]), m)
            if r.get("range", {}).get(m["name"]) and r["values"][m["name"]]:
                lo, hi = r["range"][m["name"]]
                s += f" [{fmt_value((lo, lo, lo, 'exact'), m)}–{fmt_value((hi, hi, hi, 'exact'), m)}]"
            mark = judged[m["name"]][0][i]
            if mark == "best":
                s = f"**{s}** ✓"
                cv = judged[m["name"]][1]
                if cv and cv[1] < 3 and cv[0] < fam.get("category_ratio", DEFAULT_CATEGORY_RATIO):
                    s += " †"
                    caveats.append(m["name"])
            elif mark == "lead":
                s += " ◂"
            cells.append(s)
        out.append("| " + " | ".join(cells) + " |")
    table = "\n".join(out)
    if minor:
        parts = []
        for k in minor:
            ref_v = ref["params"].get(k, "—")
            diffs = [f"{r['id']} {r['params'].get(k, '—')}" for r in rows
                     if r is not ref and r["params"].get(k, "—") != ref_v]
            parts.append(f"{k} ({ref['id']} {ref_v}; {'; '.join(diffs)})")
        out.append("")
        out.append("Also differs: " + ", ".join(parts) + ".")
    out.append("")
    legend = [("✓", "✓ best, decided"), ("◂", "◂ best of the finished rows, which a run still going could beat"),
              ("≥", "≥ lower bound (still running, or stopped before finishing)"), ("now ", "now = current value"),
              ("last ", "last = last value logged"), ("~", "~ end time taken from the log's last write")]
    used = [text for sym, text in legend if sym in table.split("|---|", 1)[-1]]
    if used:
        out.append("Key: " + "; ".join(used) + ".")
    if caveats:
        out.append(f"† decided from fewer than 3 runs a side, by a ratio under "
                   f"{fam.get('category_ratio', DEFAULT_CATEGORY_RATIO):g}×: run in triplicate "
                   f"before treating it as a measurement ({', '.join(dict.fromkeys(caveats))}).")
    # progress since the last report, for values that grow
    prog = []
    for r in rows:
        if r["status"] != "running":
            continue
        before = state.get(r["id"])
        snap = {k: v[0] for k, v in r["values"].items() if v}
        new_state[r["id"]] = {"t": now, "values": snap}
        if not before:
            continue
        dt = (now - before["t"]) / 60
        bits = []
        for m in fam["measures"]:
            if m.get("from") == "elapsed" or m["name"] not in snap or m["name"] not in before["values"]:
                continue
            d = snap[m["name"]] - before["values"][m["name"]]
            if m.get("grows") or m.get("from") == "elapsed":
                bits.append(f"{m['name']} {d:+,.3g}" if not float(d).is_integer() else f"{m['name']} {int(d):+,}")
        if bits and dt > 0:
            prog.append(f"{r['id']}: {', '.join(bits)} in {dt:.0f} min")
    if prog:
        out.append("Since the last report: " + "; ".join(prog) + ".")
    return out, rows


def fingerprint(lines):
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()[:16]


def parse_since(text):
    if text == "today":
        return datetime.combine(datetime.now().date(), datetime.min.time()).timestamp()
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        fail(f"--since takes 'today' or an ISO date or time, not {text!r}")


def active_since(runs, since):
    """some run started, or wrote its log, at or after `since`"""
    for r in runs:
        if r.get("started") and datetime.fromisoformat(r["started"]).timestamp() >= since:
            return True
        if r.get("log") and Path(r["log"]).exists() and Path(r["log"]).stat().st_mtime >= since:
            return True
    return False


def report(regpath, show_all=False, only=None, since=None):
    """only: family ids to show (each must exist); since: a timestamp.  Any of the three
    selections shows retired and closed families too."""
    reg = load(regpath)
    known = {f["id"] for f in reg["families"]}
    if only:
        unknown = [f for f in only if f not in known]
        if unknown:
            fail(f"--family {', '.join(unknown)}: no such family (known: {', '.join(sorted(known))})")
    override = show_all or bool(only) or since is not None
    procs = ps_table()
    now = time.time()
    statep = regpath.parent / STATE_NAME
    state = json.loads(statep.read_text()) if statep.exists() else {}
    new_state = dict(state)
    stamp = datetime.now().strftime("%a %d %b %Y %H:%M")
    lines = [f"## Experiments at {stamp}", ""]
    running_total = []
    any_running = False
    registered_cmds = {r["command"] for r in reg["runs"] if "command" in r}
    retired, stamps = [], {}
    for fam in reg["families"]:
        runs = [r for r in reg["runs"] if r["family"] == fam["id"]]
        if only and fam["id"] not in only:
            continue
        if since is not None and not active_since(runs, since):
            continue
        if not runs:
            if only:
                lines += [f"### {fam['question']}", "", "No runs registered.", ""]
            continue
        live = any(procs.get(r.get("pid"), {}).get("command") == r.get("command") for r in runs)
        if fam.get("closed") and not live and not override:
            continue
        out, rows = family_report(fam, runs, procs, now, state, new_state)
        if any(r["status"] == "running" for r in rows):
            any_running = True
        else:
            # every run has ended: show this final state once, then retire the family
            fp = fingerprint(out)
            if fam.get("last_reported", {}).get("state") == fp and not override:
                retired.append(fam["id"])
                continue
            stamps[fam["id"]] = {"state": fp, "at": datetime.now().isoformat(timespec="seconds")}
        lines += out + [""]
    for r in reg["runs"]:
        p = procs.get(r.get("pid"))
        if p and p["command"] == r.get("command"):
            running_total.append(p)
    if running_total:
        cpu = sum(p["cpu"] for p in running_total) / 100
        rss = sum(p["rss_kb"] for p in running_total) / 2**20
        lim = reg.get("limits", {})
        k = len(running_total)
        s = f"Load: {k} registered process{'es' if k > 1 else ''}, {cpu:.1f} cores busy, {rss:.1f} GB resident"
        flags = []
        if "cores" in lim and cpu > lim["cores"]:
            flags.append(f"over the {lim['cores']}-core limit")
        if "rss_gb" in lim and rss > lim["rss_gb"]:
            flags.append(f"over the {lim['rss_gb']} GB limit")
        lines.append(s + (" — **" + "; ".join(flags) + "**" if flags else "") + ".")
    watch = reg.get("watch", [])
    wrappers = {"timeout", "gtimeout", "nohup", "nice", "sh", "bash", "zsh", "time", "caffeinate"}
    strays = [(pid, p) for pid, p in procs.items()
              if any(w in p["command"] for w in watch) and p["command"] not in registered_cmds
              and Path(p["command"].split()[0]).name not in wrappers and pid != os.getpid()]
    if strays:
        lines.append("")
        lines.append("Unregistered running jobs matching the watch list:")
        for pid, p in sorted(strays):
            argv0, _, rest = p["command"].partition(" ")
            lines.append(f"- pid {pid}, {p['etime'] // 60} min, {p['rss_kb'] / 2**20:.2f} GB: "
                         f"`{(Path(argv0).name + ' ' + rest)[:140]}`")
    if retired:
        lines.append(f"Retired (all runs ended, final state already reported; `--family ID` or "
                     f"`--all` shows them): {', '.join(retired)}.")
    if not any_running and not strays:
        lines.append("No registered run is running.")
    if stamps:
        # reload before writing, so a run registered meanwhile by another session is kept
        fresh = load(regpath)
        for fam in fresh["families"]:
            if fam["id"] in stamps:
                fam["last_reported"] = stamps[fam["id"]]
        save(regpath, fresh)
    statep.write_text(json.dumps(new_state, indent=1))
    print("\n".join(lines).rstrip())


# ---------------------------------------------------------------- registering

def register(regpath, a):
    reg = load(regpath)
    procs = ps_table()
    p = procs.get(a.pid)
    if p is None:
        fail(f"pid {a.pid} is not running")
    log = Path(a.log).expanduser().resolve()
    if not log.exists():
        fail(f"log {log} does not exist")
    started = datetime.fromtimestamp(time.time() - p["etime"]).isoformat(timespec="seconds")
    run = {"id": a.id, "family": a.family, "pid": a.pid, "command": p["command"],
           "log": str(log), "started": started}
    if a.role:
        run["role"] = a.role
    if a.note:
        run["note"] = a.note
    reg["runs"].append(run)
    save(regpath, reg)
    fam = next(f for f in reg["families"] if f["id"] == a.family)
    print(f"registered {a.id}: pid {a.pid}, started {started}, parameters "
          f"{params_of(run, fam)}")


def record(regpath, a):
    reg = load(regpath)
    run = {"id": a.id, "family": a.family,
           "params": dict(kv.split("=", 1) for kv in a.param),
           "recorded": {k: to_number(v) for k, v in (kv.split("=", 1) for kv in a.value)},
           "source": a.source}
    if a.started:
        run["started"] = a.started
    reg["runs"].append(run)
    save(regpath, reg)
    print(f"recorded {a.id}: {run['recorded']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--registry", type=Path)
    ap.add_argument("--all", action="store_true", help="show every family, retired and closed included")
    ap.add_argument("--family", dest="show_family", action="append",
                    help="show this family whatever its state (repeatable)")
    ap.add_argument("--since", help="show families with a run active since: today, or an ISO date/time")
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("register")
    r.add_argument("--family", required=True)
    r.add_argument("--id", required=True)
    r.add_argument("--pid", type=int, required=True)
    r.add_argument("--log", required=True)
    r.add_argument("--role", help="e.g. reference")
    r.add_argument("--note")
    c = sub.add_parser("record")
    c.add_argument("--family", required=True)
    c.add_argument("--id", required=True)
    c.add_argument("--param", action="append", default=[])
    c.add_argument("--value", action="append", default=[], required=True)
    c.add_argument("--source", required=True, help="where the numbers come from")
    c.add_argument("--started", help="ISO time, for ordering rows")
    sub.add_parser("check")
    a = ap.parse_args()
    try:
        regpath = (a.registry.expanduser().resolve() if a.registry else find_registry(Path.cwd()))
        if a.cmd == "register":
            register(regpath, a)
        elif a.cmd == "record":
            record(regpath, a)
        elif a.cmd == "check":
            reg = load(regpath)
            print(f"{regpath}: {len(reg['families'])} families, {len(reg['runs'])} runs, valid")
        else:
            report(regpath, show_all=a.all, only=a.show_family,
                   since=parse_since(a.since) if a.since else None)
    except RegistryError as e:
        sys.exit(f"report.py: {e}")


if __name__ == "__main__":
    main()
