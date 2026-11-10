# The registry format

`experiments/registry.json` at the project's root. One JSON object:

```json
{
  "limits": {"cores": 10, "rss_gb": 12},
  "watch": ["mikkonen_certify.py"],
  "cadence": {"every_minutes": 30, "cron_id": "…", "since": "2026-11-10T12:30"},
  "families": [
    {
      "id": "r37-minors",
      "question": "Do 2x2 minors at the root shrink the R(3,7) m = 68 order-8 tree?",
      "program": "mikkonen_certify.py",
      "positional_names": ["s", "t", "N", "r"],
      "contrast": ["minor-rounds"],
      "minor": ["sep-rounds"],
      "defaults": {"minor-rounds": "0"},
      "ignore": ["proof", "trace-seconds"],
      "reference": "m68-noMinors",
      "done_regex": "^proof written",
      "stall_minutes": 30,
      "category_ratio": 10,
      "measures": [
        {"name": "time",  "from": "elapsed", "better": "lower"},
        {"name": "nodes", "regex": "^\\s*(\\d+) nodes,", "grows": true, "better": "lower"},
        {"name": "peak",  "regex": "peak ([0-9.]+) GB", "unit": "GB", "grows": true, "better": "lower"},
        {"name": "RSS",   "from": "rss", "unit": "GB", "better": "lower"}
      ]
    }
  ],
  "runs": [
    {"id": "m68-noMinors", "family": "r37-minors",
     "command": "python -u mikkonen_certify.py 3 7 23 8 --m 68:68 … --probe-sweeps 20 --proof …",
     "log": "/abs/path/results/probe/R37_r8_m68_noMinors.err", "started": "2026-11-10T09:32:50"},
    {"id": "m68-minors10", "family": "r37-minors", "pid": 52783,
     "command": "<exactly as ps prints it>", "log": "/abs/path/results/probe/R37_r8_m68.err",
     "started": "2026-11-10T12:03:02"},
    {"id": "m68-pp", "family": "r37-minors", "params": {"minor-rounds": "0", "m": "68:68"},
     "recorded": {"nodes": 1204, "time": 7400}, "source": "memory, 2026-11-08",
     "started": "2026-11-08T09:00:00"}
  ]
}
```

## Top level

| Key | Meaning |
|---|---|
| `limits` | optional; the load line is flagged when registered processes together exceed `cores` (busy cores, from `ps` %CPU) or `rss_gb` |
| `watch` | optional; substrings of commands to look for among running processes. A match that is not a registered run is listed as unregistered. Shells and wrappers (`timeout`, `nohup`, `zsh -c`) are skipped |
| `cadence` | optional; written when a reporting interval is agreed, so its existence is on disk |

## Family

| Key | Meaning |
|---|---|
| `id`, `question` | required. The question is the table's heading: write it as the question the runs answer |
| `measures` | required; see below |
| `contrast` | parameters the question varies. Omitted: every parameter that varies. A varying parameter outside `contrast` and `minor` gets a column and is reported as a confound |
| `minor` | parameters known to differ between runs but judged not to matter for the question. When they vary they get no column and no warning: one "Also differs:" line under the table gives each run's value where it differs from the reference row. A parameter cannot be in both lists |
| `program` | the token after which the command's arguments start (the script name). Omitted: everything after the first token |
| `positional_names` | names for positional arguments, in order (otherwise `arg1`, `arg2`, …) |
| `defaults` | the value a parameter has when its flag is absent, so `--minor-rounds` absent reads `0`, not "—" |
| `ignore` | parameters that are not part of the setting: output paths, trace intervals |
| `seed_param` | the seed's parameter; runs equal apart from it merge into one row (median, range, n) |
| `reference` | the run id of the reference row. Omitted: the earliest-started run |
| `done_regex` | matches the line a run prints when it finishes. Without it a run that has exited is "stopped" and its values stay lower bounds |
| `stall_minutes` | a running run whose log has not been written for this long is marked **silent** (default 30) |
| `category_ratio` | a decided difference from fewer than 3 runs a side, by a ratio below this, is marked † (default 10) |
| `closed` | true hides the family once none of its runs is running, without the final showing that retirement gives |
| `last_reported` | written by `report.py`, not by hand: `{"state": <fingerprint>, "at": <ISO time>}` of the final state last shown. While the fingerprint matches, routine reports skip the family. Delete it to show the family again in the next routine report |

## Measure

| Key | Meaning |
|---|---|
| `name` | column heading |
| `better` | `lower` or `higher`: required, and specific to the experiment |
| `from` | `elapsed` (start to now while running; start to the log's last write once ended) or `rss` (current resident memory, running only) |
| `regex` | instead of `from`: the last match in the log, first capture group, commas allowed in the number |
| `grows` | true if the value can only increase during a run (counts, elapsed time, peak memory). A running value is then a lower bound. `from: elapsed` grows by default |
| `unit`, `scale` | display unit, and a factor applied to the captured number |

## Run

A process run has `command` (exactly as `ps -ww -o command=` prints it; `register` copies it),
`log` (absolute path), `started` (ISO time) and, while live, `pid`. A historical run can omit
`pid`. A recorded run has `params`, `recorded` (measure name → value) and `source`; give it
`started` to place it in the row order. `params` on a process run overrides what the command
line gives. Optional on any run: `role`, `note`.

## How verdicts are reached

Each value is an interval. A finished run's value is exact. A running or stopped run's value
of a growing measure is `[value, ∞)`. A snapshot is `(−∞, ∞)`. A row is **decided best** (✓)
when its interval is at least as good as every other row's whole interval. Otherwise the best
finished value is marked ◂ when an unfinished row could still beat it, and nothing is marked
when only unfinished rows have values: a younger run's smaller count leads nothing.
