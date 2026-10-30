---
name: illustrator
description: Create static scientific figures for the salient results of a manuscript, with reproducible scripts, Markdown-ready images, consistent colours, and short legends. Use for manuscript result plots, comparison figures, and diagrams of theoretical results; animated step-by-step method demonstrations belong to Demonstrator. Does not require Adobe Illustrator.
---

# Illustrator

Make the manuscript’s key results visible at a glance. Deliver a script that regenerates each
figure, standard image files that work both in Markdown and on their own, and a short legend.
Prefer a few figures with distinct purposes over an illustration for every table.

## Find the visual claims

Read the manuscript’s abstract, results, conclusions, and the underlying tables or data.
Identify the salient results and map each proposed figure to a specific claim and source
(section, table, theorem, or data file). Respect figures the user explicitly requests.
Briefly state the selection and the intended visual takeaway, then proceed.

For numerical claims, use the project’s data or extract exact values from its tables with
source locations recorded. Do not invent observations, uncertainty, timings, or significance.
If a needed input is missing, finish independent figures and report the gap; do not fill it
with plausible values. An illustrative construction must be labelled as such in its legend.
For a proven result, show its structure or consequence without suggesting a toy example is
empirical evidence for the proof.

## Choose a visual form

Choose the form that makes the claim easiest to see: paired dots for method comparisons,
lines for ordered trends, scatter plots for relationships, or a diagram for a construction,
containment, bound, or counterexample. Avoid decorative 3D effects and redundant panels.
Use aligned panels only when they answer a shared question.

Make comparison scales consistent. Use zero baselines for bars; disclose axis breaks or log
scales. Show units, sample sizes, aggregation rules, and the meaning of uncertainty in the
legend. Timeouts are censored observations, never exact runtimes. Plot all relevant groups;
do not select only favourable cases. Do not turn a single solver timing into a general speedup
claim; numerical timing comparisons need repeated seeds and reported spread.

## Apply a consistent visual language

Use a white background, dark text, clear spacing, and restrained grid lines. Prefer blue,
red, and green for the first three series. Assign colours by method or scientific role once
for the whole manuscript: keep the same mapping across panels and figures, even when a
series is absent. Reserve grey for context and baselines; add colours only when needed.

For Matplotlib, copy `assets/manuscript.mplstyle` into the output folder as `figure.mplstyle`.
It defines basic blue/red/green. If colour-blind-friendly output is requested, replace its
`axes.prop_cycle` with blue `#0072B2`, vermilion `#D55E00`, and bluish green `#009E73`, keeping
semantic assignments fixed. These colours alone do not guarantee accessibility: distinguish
series with markers, dash patterns, hatching, or position as well. Check greyscale and, when
available, colour-vision simulation; report what was actually checked.

Keep text inside the figure minimal: axes, units, short series labels, panel letters, and
an occasional short annotation directing attention to the result. Put explanations and the
conclusion in the accompanying legend. Avoid paragraph text, long titles, tiny labels, and
legends covering data. Use clear shapes and contrasts so the key point survives thumbnail
viewing. Target readable type at final manuscript size (usually 9–11 pt).

## Produce reproducible artifacts

Use the manuscript’s existing figure directory, or create `<project>/figures/illustrator/`.
Do not overwrite existing unrelated figures. Give each result a descriptive hyphenated stem,
such as `bound-comparison`. Deliver:

- `bound-comparison.py`: a complete regeneration script, normally Python with Matplotlib.
- `bound-comparison.png`: Markdown-compatible image, normally at least 300 dpi.
- `bound-comparison.svg`: a vector image for standalone viewing and resizing; add PDF if
  the manuscript toolchain needs it. For dense raster content, PNG plus PDF is acceptable.
- `figures.md`: each image embedded with relative paths and meaningful alt text, followed
  by a short legend (normally 1–3 sentences), source locations, and regeneration commands.
- Local data, style files, and dependency versions needed to rerun the scripts offline.
  Reference durable project inputs by relative path when copying them would duplicate data.

Scripts must locate inputs relative to their own file, expose meaningful input/output options,
and run without a notebook, GUI, network, or an installed copy of this skill. Record Python
and package versions and an exact example command. Fix random seeds where randomness is
needed; avoid timestamps or unstable ordering in the figure. Derive plotted summaries from
inputs and fail on invalid or missing data. Preserve an extracted table as a local input
with its source recorded rather than burying unexplained numbers in drawing code.

Use standard plotting or vector tools for scientific figures. A generated bitmap is not a
substitute for a data-driven plot or an exact mathematical construction. Do not require
Adobe software. Do not edit the manuscript merely to insert figures unless requested;
provide the ready-to-paste Markdown instead.

Example in `figures.md` (paths relative to that file):

```markdown
![Bounds for each instance size, distinguished by colour and marker](bound-comparison.png)

**Figure 1.** The new bound is tighter across the tested sizes. Circles and squares denote
new and baseline bounds; lower values are tighter.
```

Adapt the legend to the actual supported result. When embedding from another manuscript
folder, adjust the relative image path accordingly.

## Regenerate and inspect

Run each delivered script, verify its inputs against the cited source, and inspect every
image at intended manuscript width and standalone size. Check clipping, overlaps, contrast,
units, series assignments, and whether the salient result is immediately visible. Inspect
the vector export too when tooling permits. Regenerate after fixes and run once from a
different working directory to catch hidden path dependencies.

Confirm that `figures.md` links resolve and that a second run preserves plotted values,
labels, and layout; byte identity is unnecessary when exporters add metadata. If dependencies
or rendering tools are unavailable, state the unperformed checks explicitly rather than
claiming the figure was verified. Finish with links to figures, legends, scripts, and exact
regeneration commands, plus any missing inputs or remaining limitations.
