# PeerReviewer — original prompt

Given 2026-10-30, in chat. Verbatim:

---

The PeerReviewer is a skill that emulates a highly competent, yet highly constructive, peer reviewer. Its main features should be: -a primary focus on methods, evaluated on their own merits -a secnodary focus on presentation, readability and clarity, as well as the ease of reproducing the results (for our internal papers, the reproduction repository can be assumed to address this goal) -if necessary, the LitReviewer skill (currently a placeholder occupied by Undermind, but that may change) can be used to put it into the context of previous literature; this will help evaluate the manuscript's novelty and contribution -the review should contain no more than 5 major and 10 minor points, as the skill will be called upon in a loop (review - fix - confirm - review etc) -my own reviews found in @~/Downloads/Reviewing/ can be used as a guide for style and depth, but please limit extraction to only those papers that have been (eventually) published and are accessible without copyright violations, as per the hook already present in this project.

---

## Context at the time (2026-10-30)

- Prompted by a trial of Google Deep Review on the BME manuscript. His verdict: "quite
  superficial (more copy-editing, less substance), although many suggestions are still useful."
  That report is at
  `~/Downloads/Phylogenetics/BalancedMinEvolution/Manuscript/reviews/2026-10-30_deepreview.md`
  and serves as a baseline the skill should beat.

## Design decisions (answers given 2026-10-30)

- **Loop:** confirm, then review. Given the previous review, first mark each earlier point
  resolved / partly / not resolved, then add new points; the 5 major + 10 minor cap applies to
  the open points (carried over plus new).
- **Verdict:** none. Points only; the loop decides when to stop.
- **Architecture:** one reviewer voice writes the review; it may spawn a few subagents to verify
  specific proofs or claims before raising them as points.
- **Test cases:** the BME manuscript first; later, published open-licence papers he reviewed,
  where his actual review is the reference answer.
- **Baselines:** Google Deep Review's report on BME (2026-10-30) and the co-scientist-toolkit
  `paper-review` skill (multi-agent panel; installed 2026-10-26, so it did NOT produce
  `reviews/2026-10-01_external_review.md`, which predates it).
- **Test input for published papers:** the open preprint where one exists (closer to the reviewed
  version). His words on mismatches: "if you can't find the issues I pointed out in those
  preprints, then you can still assume they were there when I reviewed". So a point of his that
  the preprint no longer shows is still a genuine point (valid as a style/depth example); in
  grading, it counts as not findable in that input rather than as a miss by the skill.
- **Borrowed from paper-review (agreed 2026-10-30):** the Devil's Advocate mandate (the
  strongest objection to the main claim, plus what would defeat it). paper-review itself is run
  as a baseline on BME, Phases 1–2 only, once.

## Revisions after iteration 1 (his answers, 2026-10-30)

- **Length:** "give it 1000 words". Points two to four sentences.
- **Hand-off:** "as a nice illustration of skills working together it's helpful to do a
  /scientific-humanizer pass on its review after the fact (especially if the review is to be
  used for internal collaborators' work rather than our own)".
- **Consistency pass** in the reading step (captions vs cells, an inequality listed twice,
  every pseudocode choice specified): "agreed on the choice".
- **"Is a stronger statement available from the same proof?"** for each theorem: "helpful, so
  let's add".
