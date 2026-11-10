---
name: experiment-reporter
description: Report on running computational experiments as a table that sets each run against the settings it is compared with, giving its parameters, the contrast being tested, the measures that answer the question (time, memory, search-tree size, bounds) for this run and the earlier ones, and which is better, marked only once that is decided. Runs are kept in a registry in the project, so each report comes from the processes and logs themselves and not from memory. Use this whenever the user says "please report", "update me", "how are the runs going", "where are we with the experiments" or asks for the status of running jobs, when a report is due at an agreed interval ("report every 30 minutes"), and when launching an experiment or benchmark run that should be compared with earlier settings, so it is registered at launch.
---

# Experiment-Reporter

This skill answers "please report" with the same kind of table each time. The table lists
the runs that answer one question, the parameter being varied, each run's measures beside
those of the earlier settings, and which run is better. A run is called better only when the
numbers decide it. The table is produced by `scripts/report.py` from a registry kept in the
project, the live process table and the runs' own logs. Every number comes from the script.
None is retyped or remembered.

## The registry

The registry is `experiments/registry.json` at the project's root, and it is tracked in git
like any other record of the work. `references/registry.md` gives the format, with an
example. It holds two kinds of entry.

- **A family** is one question, for example "do 2×2 minors at the root shrink the R(3,7)
  m = 68 tree?". It names the contrast, which is the parameter or parameters the question
  varies. It also lists the measures that answer the question. Each measure states which
  direction is better and where its value comes from: elapsed time, the process's resident
  memory, or a regular expression matched against the log's progress lines.
- **A run** is one setting of the question. It is either a process registered at launch
  (its command, pid, log and start time) or a result recorded earlier and not rerun, with
  its source.

The script reads each run's parameters from its command line, so the contrast is computed
and not described. Parameters shared by every run go on one "Fixed" line. Those that differ
become columns, and a value that differs from the reference row is in bold. If two runs
differ in a parameter outside the declared contrast, the report says the comparison is
confounded.

Some differences are known and judged not to matter, such as a trace setting or a pruning
interval that changed between campaigns. List these under the family's `minor` key. They
then get no column. Instead, one "Also differs:" line under the table gives each run's
value. Move a parameter to `minor` only after you have decided it does not bear on the
question, and say so in the report the first time. Hiding a real confound there defeats the
warning.

### Setting up a family

Do this once per question, before the first report.

1. **Ask which direction is better if it is not obvious.** Time, memory and node counts
   are lower-is-better. A bound, the fraction of the tree closed, or a margin can go either
   way, and only the user knows which way this experiment needs. Record it as `better`.
2. **Mark the measures that only grow during a run.** These are elapsed time, nodes, peak
   memory and counts of anything. Mark them `"grows": true`. A running run's value of such a
   measure is then a lower bound on its final value, and the verdicts depend on that. A
   value that can move both ways, such as current memory or the current gap, is a snapshot
   and decides nothing until the run ends.
3. **Test every regular expression on the real log before relying on it.** Run
   `grep -E '<regex>' <log> | tail -2` and check that the capture group holds the number
   meant. If a log prints a summary line on success, put a `done_regex` matching it on the
   family. Without one, the script cannot tell a run that finished from one that stopped.
4. **List under `ignore` the parameters that are not part of the setting.** Typical ones are
   output paths, trace intervals and the proof file name. If runs are repeated with
   different seeds, name the seed parameter as `seed_param`. Runs that differ only in the
   seed then merge into one row, which gives the median, the range and the number of runs.

### Registering a run

Register a run in the same step that launches it. A run that is not registered does not
appear in the report, apart from the warning described below.

```sh
python3 <skill-dir>/scripts/report.py register --family r37-minors --id m68-minors10 \
    --pid 52783 --log results/probe/R37_r8_m68.err
```

The script reads the command and start time from `ps`, so give the pid of the process doing
the work, not that of a `timeout` or `nohup` wrapper. An earlier result that will not be
rerun goes in with `record`, with its source:

```sh
python3 <skill-dir>/scripts/report.py record --family r37-minors --id m68-pp \
    --param minor-rounds=0 --value nodes=1204 --value time=7400 --source "memory, 2026-11-08"
```

Use `record` when the earlier setting's result is already known (from a log, memory or a
report). Do not rerun it to fill a table row.

## Making a report

1. Run `python3 <skill-dir>/scripts/report.py` from the project, or pass `--registry`.
   If it stops with an error, the registry is wrong, for example a log has gone missing or
   a family is unknown. Fix the registry and do not report around it.
2. **Paste the script's output as it stands**: the tables, the key, the load line and the
   warnings. Do not retype or round its numbers.
3. **Add at most five lines below it**, in this order:
   - **warnings**: a run marked **silent** (its log has not been written for the family's
     `stall_minutes`, 30 by default), unregistered jobs, a load over the limits, a
     confounded comparison;
   - **what changed since the last report**: the script prints the change in each growing
     measure;
   - **anything waiting on the user's decision.**
4. **Claim no more than the marks support.**
   - ✓ means decided.
   - ◂ means the best of the finished rows, which a run still going could beat.
   - ≥ means a lower bound.
   - † means a single-run ratio below the family's `category_ratio` (10× by default). By the
     user's triplicate rule this is not yet a measurement, so say "faster on one run", not
     "faster".
   - Do not turn ◂ or ≥ into a conclusion.
5. **Deal with unregistered jobs.** If the report lists running jobs that match the
   registry's `watch` list but are not registered, register each one in its family. If its
   question is unclear, say what the job is and ask.

Keep the table narrow enough not to wrap in a terminal. Use short run ids, and leave out a
measure that the current question does not need.

## Reporting at an agreed interval

When the user agrees an interval ("report every 30 minutes"):

1. Schedule it with `CronCreate`, using the prompt "Run the experiment-reporter skill: a
   scheduled report". `/loop` also works.
2. Write the interval and the job id into the registry's `cadence` field, so that "is the
   reporter still running?" has an answer on disk.
3. Tell the user once that the schedule lasts only as long as this session.
4. When a scheduled report finds that no registered run is still running, give that report
   and cancel the schedule (`CronDelete`). Do not keep reporting an empty table.

A scheduled report follows the same steps as a requested one. If nothing changed since the
last report except elapsed time, say so in one line under the table.

## What the script guarantees

- **Hard failures.** It stops with an error naming the guarantee that broke if the registry
  is invalid, if a run names an unknown family, if a measure's regular expression is
  malformed or has no capture group, if a contrast parameter appears in no run, or if a
  registered log has disappeared.
- **Missing values.** A measure that has not printed yet shows "—". This is not a failure,
  because a run's first progress line may not have been written yet.
- **Running processes.** A pid counts as running only if its command line is still the
  registered one, so a reused pid is not mistaken for the run.
- **Self-test.** `scripts/selftest.py` checks the verdicts on synthetic runs:
  - a running lower bound blocks a decision;
  - a stopped run stays a lower bound;
  - a finished run decides;
  - replicates merge;
  - a confound is named;
  - a broken registry stops the report.
  
  Run it after any change to `report.py`.
