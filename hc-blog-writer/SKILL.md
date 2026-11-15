---
name: hc-blog-writer
description: Write a blog post for the HerdingChickens (HC) website that meets SEO and answer-engine (AEO/GEO: being quoted by ChatGPT, Perplexity and Google AI Overviews) criteria while keeping HC's house style - bite-sized, one actionable tip, respectful of ADHD readers, plain words, no fabricated citations. Picks a keyword from Stéphane's Ubersuggest position-tracking export (skipping keywords existing posts already target), drafts the post in the website's frontmatter format with published false, verifies every external source, runs a humanizer pass, and scores the draft against a register of named, switchable rules (Connor Gillivan's SEO checklist, AEO rules and Leonid's house rules), producing a checklist report. Use this whenever someone asks to write, draft, outline or SEO-check a HerdingChickens / HC blog post or resource article, pick the next HC blog keyword, or check a draft against the HC blog checklist.
---

# HC blog writer

Writes one HerdingChickens blog post at a time, the way both founders agreed in the website repo's
`docs/BLOG-STRATEGY.md`: easy to find (Stéphane's side) and worth trusting (Leonid's side). The output
is a Markdown file in the site's format with `published: false`, its sources ledger, and a checklist
report. A person reviews it and publishes it; this skill never touches the website repo.

## Files

| File | What it holds | Who edits it |
|---|---|---|
| `rules.toml` | **Every rule, its on/off switch, its numbers and a one-line reason.** The policy lives here and nowhere else. | Stéphane and Leonid |
| `references/checklist.md` | Gillivan's checklist item by item, mapped to rules, with what is off and why | when the list changes |
| `references/aeo.md` | What credible sources say about being quoted by answer engines, and the rules that follow | when guidance changes |
| `references/house-style.md` | Voice, respect rules, sources ledger, links, post shape, humanizer pass | Leonid |
| `references/sources.md` | The sources behind the rules, with the date read | with `aeo.md` |
| `references/ai-tells.md`, `plain-strong-writing.md` | Links to `shared/`, used by the humanizer pass | in `shared/` only |
| `assets/post-template.md` | The frontmatter and section skeleton | when the site format changes |
| `scripts/keywords.py` | Ranks an Ubersuggest export and marks what the blog already covers | |
| `scripts/check_post.py` | Scores a draft against `rules.toml`, optionally fetching every link | |

**To change a rule**, edit its `on` and `why` in `rules.toml`. Switched-off rules still show in the
report as OFF, with what the result would have been, so the trade-off stays visible. Adding a new
automatic rule means a matching function in `check_post.py`; the script stops with an error if the
two lists disagree.

## Inputs

- **Keywords:** an Ubersuggest position-tracking export, CSV with columns `Keyword, Position, Change,
  Search Intent, Volume, SEO Difficulty, URL`. Ask for the latest one if none is given; the last known
  was `~/Downloads/position-tracking-report-2026-10-30.csv`.
- **Existing posts:** the website repo's `content/blog/` folder (default
  `~/Downloads/herding-chickens-website/content/blog`). Read-only.
- **The author:** whose voice and byline. Default Leonid.

## Workflow

### 1. Pick the keyword

```sh
python3 <skill-dir>/scripts/keywords.py EXPORT.csv --site-blog <content/blog> --top 25
```

Choose from the FREE and SECONDARY rows near the top: high volume, difficulty you can reach (the
export's own numbers; around 30 or below has been reachable). Skip TAKEN and RANKS, merge NEAR-DUPs
into the keyword they duplicate, and skip anything a live post covers under a synonym (the script
cannot see that "adhd executive function" and "executive dysfunction adhd" are one search). For a
SECONDARY keyword, give the new post an angle the existing post does not cover, and note in the report
that the old post's `secondary_keywords` entry should go when the new post is published. Also skip
keywords that contain deficit words (house rule) and competitor brand names unless asked.

### 2. Outline before prose

Read two of Leonid's posts for voice, and `references/house-style.md`. Then write the outline: title,
the short-version rows, the H2s (one a question), the FAQ questions, and the one thing to do today.
If the user is in the loop, show the outline first: per BLOG-STRATEGY the outline is the real gate.

### 3. Find sources before writing claims

List every factual claim the outline needs. For each, open a source and copy the supporting passage
into `<slug>.sources.json` (format in `house-style.md`). If no source says it, the claim becomes
experience ("many of us find…") or goes. Never write a citation from memory, and never let a source
say more in the post than it says on the page (population, year, whether it is about ADHD at all).
Open every paper link, including ones already in a post you are editing, and compare the paper's
title and abstract with the sentence (`paper_title_matches`). If they do not match, or nobody could
open it, write `[SOURCE NEEDED]` and stop; never swap in a different unopened paper.

### 4. Draft

Start from `assets/post-template.md`. Fill the frontmatter (`published: false`; `cover` and
`cover_alt` are added by a person with the photo, so leave them out). Put the author's own experience
in `[AUTHOR: ...]` slots; never invent it. Link 2-4 existing posts in `related` and Keep reading, at
least one of them in the body. Name one sentence in an existing post, already about this idea, that
should carry an inbound link (`inbound_link`). Keep secondary keywords to phrases with real demand
(`low_volume_secondaries` in `rules.toml` holds the threshold); never add a section to host one.

### 5. Humanizer pass

Apply the pass in `house-style.md` using `references/ai-tells.md`: casual blog register, at most one
idiom, at most one em-dash. Read it aloud.

### 6. Check and report

```sh
python3 <skill-dir>/scripts/check_post.py <post>.md --site-blog <content/blog> --check-links --out <post>.report.md
```

Fix every FAIL that is the draft's fault and look at every WARN. Then answer each MANUAL row by hand,
appending a short section to the report:

```
## Manual checks
- title_not_clickbait: PASS. <one line>
- lived_experience: OPEN. 1 [AUTHOR] slot for <author>.
- final_edit: PASS. Humanizer pass done; read aloud.
```

`--check-links` asks NCBI's E-utilities whether a PubMed or PMC ID exists and prints its title, because those sites answer a made-up ID with a normal-looking page; compare the title with the ledger. A link that answers 403 to the script (publisher bot walls) is checked in a browser or through the
publisher's abstract page, and the report says which.

## SEO pass on an existing post

When asked to improve a post that already exists (an editorial or SEO brief), the author's sentences
stay theirs (`keep_author_paragraphs`). Change only the chrome: title, `meta_description`,
`focus_keyword` and `secondary_keywords`, the keyword once in the opening in the author's spoken
register, the one worked example the brief names (short, using a task the post already mentions, no
invented facts or features), and the links the brief names. Leave `published`, `date`, `slug`,
`cover` and `cover_alt` alone. Set `updated:` only if the body changed materially
(`no_fake_freshness`). Re-open every paper link. Run the checker with `--site-blog` so a focus keyword
shared with another post, as focus or as secondary, shows up. Report every paragraph touched, with the
new sentences quoted, and a short plain note for whoever publishes.

Publishing is a person's step and follows `publish_cadence`: one new or materially updated guide on
the public site per window, never a batch in one week, however many drafts are ready.

## Output

Save in a workspace folder, never in the website repo (default: `hc-blog-writer-workspace/` beside
the skill, or wherever the user says; the repo's `.gitignore` keeps `*-workspace/` out of git):

- `<slug>.md`: the post, `published: false`
- `<slug>.sources.json`: the sources ledger
- `<slug>.report.md`: the checklist report plus manual checks

Then tell the user, briefly: the keyword and why it was chosen, the file paths, the FAILs and WARNs
left and why, any open `[AUTHOR]` slots, and anything that could not be verified.

## Things that are not this skill's job

Publishing, choosing the cover photo, editing existing posts unasked (a SECONDARY clash is reported,
not fixed, unless a brief asks for the SEO pass above), and site-level items (robots.txt, page speed,
share buttons, publishing cadence), which the report lists as SITE.
