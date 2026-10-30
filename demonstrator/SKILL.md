---
name: demonstrator
description: Build an animated, step-by-step demonstration of a method used in a manuscript or research project, run on the smallest example that makes the method interesting. The method is executed for real by a small script, and every number shown comes from that run. The result is a self-contained interactive HTML page (narrated steps, play controls, full-screen presentation mode, a short quiz) plus an MP4, a GIF and PNG key frames for slides. Use this whenever the user asks to demonstrate, animate, visualise, illustrate or explain a method, algorithm or construction step by step, wants a figure or animation for a talk, workshop, lecture or paper, asks "show me how X works on a small example", or mentions the Demonstrator; for example Kelley's cutting-plane method, neighbour joining, branch and bound, a separation routine or a proof construction from their own paper.
---

# Demonstrator

A method is understood when you have watched it work on an example small enough to hold in
your head. This skill builds that example: it picks the smallest instance on which the method
shows everything it does, runs the method on it, and turns the run into a narrated animation.
Words and pictures carry the explanation together. Each step changes one thing on the screen,
and its narration says what changed and why.

The same spirit as `explain-diff-html`: a single self-contained page, background before
detail, toy data, diagrams over prose, and a quiz to check understanding.

## Principles

1. **Computed, not drawn.** A script runs the method and records every step. The page draws
   from that record and never from numbers typed by hand. If the method is implemented in
   the project, call that implementation. Otherwise write a minimal, faithful one and say so
   on the page. Assert the method's guarantees in the script (a lower bound never decreases,
   a cut never removes a feasible point), so a wrong demonstration fails loudly, not
   quietly.
2. **Smallest interesting example.** List the moves and behaviours that make the method what
   it is, then pick the smallest instance that shows each of them at least once. If removing
   any part of the example would lose one, it is small enough. Prefer round, readable inputs.
   Say on the page why this example and nothing smaller.
3. **One change per step.** The newest element is drawn in the accent colour, older ones
   fade. The axes and scale stay fixed across steps (rescaling makes viewers lose their
   place). Every step's narration says what happened, why, and what it means, in at most
   three sentences.
4. **Tied to the paper.** The point is how the method behaves *in this project*: use the
   paper's variant, parameters and notation, quote where the paper uses it, and show on
   the example the behaviour that matters there (for instance the numerical difficulty
   the paper reports).

## Workflow

### 1. Find the method in the project

Read where the manuscript or code uses the method: which variant, on what objects, with what
parameters, and what the paper says about it (including problems it reports). Quote the
passage, with its section. If the user names a method the project does not use, demonstrate
its standard form and say so.

### 2. Choose the example

Write down, before any code:
- the method's moves (what it does at each step) and the behaviours a viewer should see
  (convergence, a bound tightening, a tie being broken, a case where it fails);
- the smallest instance that shows all of them. For a geometric or numerical method that is
  usually one or two dimensions; for a combinatorial one, the fewest items for which every
  case arises (for neighbour joining, five taxa: four leave only one joining decision);
- the number of steps, aiming for 6 to 15: a setup step, one per meaningful move, and a
  closing step stating the result.

If the paper's real use is larger, add a second, short part after the minimal example that
moves one step closer to it (for example from a convex function to a constraint), rather
than making the first example bigger.

**Show the failure, do not only describe it.** If the method can go wrong in a way that
matters to the paper (NJ missing the BME optimum, a cutting plane stalling), find the
smallest instance where it does, and animate it as its own part of the trace, with its own
steps. A failure that only appears as prose under "What can go wrong" is one the audience
never sees.

### 3. Compute the run

Create the demonstration folder in the project: `<project>/demos/YYYY-MM-DD-<method>/`
(today's date; create `demos/` if needed; if there is no project folder, ask where). In it,
write `compute.py`, which:
- runs the method on the example and writes `trace.json`: `{"title", "stepMs", "legend":
  [[colour, label], …], "parts": [{"title", "step"}, …], "steps": [{"title", "narration",
  "legend"?, …whatever drawStep needs}]}`. `parts` (when there is more than one) gives each
  part a button and a direct link (`?part=2`). A step's own `legend` replaces the trace's,
  so each part lists only the objects it draws;
- formats every number in the narration from the computed values with `num` from
  `scripts/numfmt.py` (4 significant figures, at most 5, and scientific notation below
  10⁻³ or from 10⁵, so a gap converging to zero reads 2.1 × 10⁻⁶ and never 0.00). In
  `drawStep`, the template's `num()` does the same;
- writes formulas in the narration as HTML (`x<sub>2</sub>`, `2<sup>−τ</sup>`) or MathML,
  never as ASCII (`x^2`, `w_T`);
- asserts the method's invariants and the expected result, and fails if they do not hold.

Colours are `c1`…`c5` and `muted`, which the template themes for light and dark.

### 4. Build the page

Copy `assets/player.html` to `<method>.html` in the folder. It contains the player (controls,
keyboard, presentation mode, URL parameters, quiz) and a small SVG helper, `Plot`
(`axes`, `clip`, `fn`, `path`, `area`, `line`, `dot`, `label`, with data coordinates). Edit
only the parts marked `DEMO`:

- **Title and subtitle**: the method, and which paper and section uses it.
- **Sections**, in the fixed order (keep the ids): *The method* (what it computes and the one
  idea that makes it work, in plain words, with a formula in MathML if it helps); *The
  example* (what the example is and why it is the smallest interesting one); *Step by step*
  (the stage); *In the paper* (the quoted use, and how the example maps to it); *What can go
  wrong* (the failure modes that matter here, shown on the example where possible); *Check
  yourself* (the quiz). Open each section with a sentence saying what it does, and end with
  one leading into the next. Define every term before first use. Write plainly, in the clear,
  classic style of `explain-diff-html` (Kleppmann). Use MathML for formulas: the page must
  work offline, so no CDN.
- **Legend**: short labels, at most four words each (`embed_trace.py` refuses longer ones); the
  explanation belongs in the narration. The legend wraps onto several lines by itself.
- **`drawStep(svg, trace, k)`**: draws step `k` from `trace.steps[k]` alone. Fix the plot
  ranges for the whole run. Draw areas first, then lines, then points and labels. Label
  things on the plot where possible, not only in the legend.
- **Quiz**: five multiple-choice questions of medium difficulty that need the example to
  answer (what happens at a given step, why a bound moves, what would change with a
  different start), each with a one-sentence explanation. Write them to `quiz.json`.

Then embed the computed data:

```
python3 <skill-dir>/scripts/embed_trace.py <method>.html trace.json --quiz quiz.json
```

Rerun this whenever `compute.py` changes.

### 5. Render the media and look at it

```
python3 <skill-dir>/scripts/render_media.py <method>.html            # light theme, 1600x900
python3 <skill-dir>/scripts/render_media.py <method>.html --theme dark --out media-dark
```

This writes `media/frames/step-NN.png`, `media/<method>-auto-run.mp4` and
`media/<method>-auto-run.gif`. **Look
at the first, a middle and the last frame** (and one dark frame). Fix overlapping labels,
clipped elements, unreadable text at slide size, and anything that changes scale between
steps. Re-render after each fix. Open the page itself once, at phone width too, to check the
sections and the quiz.

### 6. Report

Give the folder path, a one-line description of the example and why it is minimal, the list
of steps (one line each), and the media files. Mention any part of the method you
reimplemented rather than calling the project's code.

Present the two forms of the demonstration by name, with how to use each in a talk:
- **Clickable**: `<method>.html?present=1` shows the demonstration alone, full screen, and
  the presenter moves through it at their own pace (arrow keys, Space to play, pausing at
  will). Open it in a browser tab during the talk, or embed it in slides that accept a web
  page (a web-viewer add-in, or an `<iframe>` in HTML slides). The full page, with the
  explanation and quiz, is for reading on one's own.
- **Auto-run**: `media/<method>-auto-run.mp4` plays by itself; insert it into PowerPoint,
  Keynote or Google Slides as a video. The GIF is for places that take no video.

Give a direct link to each part, above all to a failure case (`<method>.html?part=2`), so
nobody has to hunt for it.

## Files

- `assets/player.html`: the page template (player, theme, `Plot` helper, quiz), with a
  three-step bisection example in place to show the expected shape of a trace.
- `scripts/embed_trace.py`: puts `trace.json` and `quiz.json` into the page, after validating them.
- `scripts/render_media.py`: key frames and the auto-run MP4 and GIF from the page (headless Chrome and ffmpeg).
- `scripts/numfmt.py`: `num(x)`, number formatting for the narration (significant figures, scientific notation).
