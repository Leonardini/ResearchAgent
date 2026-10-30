# LitReviewer — original prompt

Given 2026-10-30, in chat. Verbatim:

---

Next we are going to develop our own LitReviewer skill. We will distinguish two cases: a paper-focused one, where we primarily review the papers relevant to our project, and a broader one, where we also include preprints, blog posts, and similar (the latter will be targeted towards fast-moving research areas). The output should be:
-an interactive webpage where each relevant article or preprint or post is listed, with a hyperlink
-colour-coded by relevance (red being the highest-risk for overlap with the current project)
-sorted by date
-if the project is already active, additionally identifying the overlap between what was achieved in the relevant material and what the project is targeting

---

## Context at the time (2026-10-30)

- Skill 6 of ResearchAgentSkills. Until now the LitReviewer role was a placeholder filled by
  Undermind (connected as an MCP server); PeerReviewer's prompt calls on it for novelty checks.

## Design decisions (answers given 2026-10-30)

- **Sources:** scripted APIs (OpenAlex, Semantic Scholar, arXiv; citation-graph expansion from
  the project's own references) plus Undermind deep search as a second, independent net. Broad
  mode adds web search for blogs, bioRxiv/medRxiv, project sites, repositories and lab posts.
- **Colours:** 3 levels. Red: overlap risk (the item does, or partly does, what the project
  targets). Amber: closely related (same problem by other means, or a method the project builds
  on or competes with). Green: background.
- **Re-runs:** incremental ledger. Every item seen is kept with its verdict; a re-run searches
  again, marks items new since the last run, re-checks verdicts if the project's goals changed,
  and never silently drops an item. The page has a "new since" filter.
- **Test cases:** BME (paper mode) and the no-three-in-line project
  (`~/Downloads/NonPriority/Conjectures/NoThreeInALine`). The last has a lit review written by
  another agent on 2026-10-30 (`LIT_REVIEW_2026-10-30.md`, Undermind + Flammenkamp's site, OEIS,
  blogs, GitHub); it is the known answer for that eval and must be hidden from the skill's input.
  Its live record sits mostly outside papers, so it doubles as the broad-mode test.
- **OpenAlex key:** he asked me to request one with his email (done 2026-10-30, pending his click
  on the activation email). Stored at `~/.config/openalex/api_key` (mode 600), outside every repo;
  the script also reads `OPENALEX_API_KEY` and falls back to keyless calls if the key is refused.
- **Paper mode and preprints (my default, not yet confirmed by him):** paper mode does not search
  for posts or repositories, but keeps a preprint that is a real overlap risk.

## His feedback on iteration 1 (2026-10-30, viewer; BME and no-three pairs)

- BME with skill: "Looks good, slightly terse. It would be particularly helpful to provide links to
  anything you have not been able to retrieve so I can cross-check as needed. I will authorise
  OpenAlex before we go to the next iteration, please remind me to do so if you still cannot
  access it then. I also found the HTML page layout very nice and easy to use, the only addition
  that could be helpful (which is where we can invoke the Referencer skill that we already have)
  is visualising the exact passage that corresponds to an overlap, rather than just a summary."
- BME baseline: "Somewhat difficult to compare given that this one included Undermind and the one
  with the skill did not; it will be best to reserve Firecrawl to cases where your own Web
  retrieval is insufficient. Otherwise all really useful findings."
- No-three with skill: "This is great, the amber should become red as soon as it's clear that it's
  in direct competition with what we are trying to do. [...] I would also want to allow
  prioritising by overlap rather than year, which is currently a toggle and not a sorting order.
  The target selection is a nice touch."
- No-three pages could not be opened in the viewer (cause: the viewer embeds only top-level files
  of outputs/; pages sat in outputs/project/. Fixed by copying each page to outputs/review_page.html).

Applied: `competing` overlap verdict (red); sort "Overlap risk, then newest"; "Not read in full"
list with links on the Summary tab and in the reply; fuller reply; Firecrawl only as fallback;
verified passages via the Referencer's module (`fulltext`, `find`, passages checked in `assess`,
shown with a page link; every red item needs one).

## Further feedback (2026-10-30, evening)

- A grader flagged as a discovery a paper that the project already cites. Lesson for the skill:
  read the project's own reference list into the brief and mark items the project already cites
  as known, so they are not presented as discoveries.
