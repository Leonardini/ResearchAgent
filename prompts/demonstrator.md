# Demonstrator — original prompt

Given 2026-10-24 (dictated by the user to his other agent, pasted here). Verbatim:

---

For any method used in a manuscript or research project, the demonstrator creates an animated example showing how that specific method applies to a very small example, ideally the smallest example that makes it interesting.
It gives a detailed explanation, not just in words but also visually, of what the method is going to do.
Similar in spirit to the explain-diff-html skill he imported recently.
Prototype / first test case: approximating a convex function with its Kelley tangents (Kelley's cutting-plane method: the convex function approximated from below by the maximum of its tangents), the method he used recently in his balanced minimum evolution project. A nice visual for the workshop, and a good way to test the skill.

---

## Design decisions (answers given 2026-10-24)

- **Output:** a self-contained interactive HTML page (step/play controls, narration synced to
  each step, full-screen presentation mode) plus an MP4/GIF of the animation and PNG key frames
  for slides.
- **Quiz:** yes, five medium-difficulty multiple-choice questions at the end (as in
  explain-diff-html), hidden in presentation mode.
- **Location:** inside the project, `<project>/demos/YYYY-MM-DD-<method>/`, with the HTML, the
  media, and the script that computes the example, so the numbers can be regenerated.

## Review feedback, iteration 1 (2026-10-26)

His comments in `demonstrator-workspace/iteration-1/feedback.json`, and what changed:

- **Kelley, with the skill:** "a very nice demo, exactly the kind of thing I'd put in a video
  abstract". The legend should have fewer words, or be shown on several lines.
- **NJ, with the skill:** the visuals are great, and the same legend caveat applies. It was
  unclear from the response how to reach the example where NJ goes wrong.
- **Kelley, baseline:** the interactivity is nice, but:
  - the gap was shown to too few significant figures, so it quickly read 0.00; use scientific
    notation;
  - the maths was written awkwardly as text; it should be LaTeX or similar;
  - the walk-through order should be separate from the demo, or there should be instructions
    for embedding just the demo in a presentation.
- **NJ, baseline:** clean, with slightly overwhelming colours. He liked stepping through one
  step at a time. Ideally there are both outputs, named "clickable" (the presenter controls
  the pace and can pause) and "auto-run" (as in the skill's versions).

Changes:
- **Legend:** labels of at most four words (`embed_trace.py` refuses longer ones). The legend
  wraps onto several lines. A step can carry its own legend, so each part lists only what it
  draws; this also fixes the earlier note that the Kelley legend mixed Part 1 and Part 2.
- **Parts:** a `parts` list in the trace gives each part a button and a direct link
  (`?part=2`). A failure that matters must be animated as its own part, not only described
  in prose, and the report links to it directly.
- **Numbers:** `scripts/numfmt.py` `num()` for the narration and `num()` in the template give
  4 significant figures, and scientific notation below 10⁻³ or from 10⁵.
- **Maths:** formulas in the narration as HTML sub/sup or MathML, never ASCII.
- **Two named outputs:** "clickable" is `<method>.html?present=1`, the stage alone, paced by
  the presenter; `&autoplay=1` makes it run by itself. "Auto-run" is
  `media/<method>-auto-run.mp4` (and `.gif`). The report says how to use each in a talk:
  - a browser tab or a web-viewer or iframe embed for the clickable one;
  - inserted as a video in PowerPoint, Keynote or Google Slides for the auto-run one.
- **Review tool:** the review page was broken because the demo pages' `</script>` ended the
  page's own script early. `tools/review_viewer.py` wraps the review tool and fixes this.
