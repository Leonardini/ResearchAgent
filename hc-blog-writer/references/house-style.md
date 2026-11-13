# HerdingChickens house style

The voice reference is Leonid's live posts in the website repo's `content/blog/` (for example
`adhd-planner-do-the-right-thing.md`, `try-a-sprint.md`, `when-just-do-it-doesnt-work-break-it-down-instead.md`).
Read two of them before drafting. The rules below are Leonid's; the checker enforces the ones it can.

## Who is reading

An adult with ADHD, or who suspects it, who searched a phrase and has a couple of minutes of
attention. They have read a lot of advice that assumes they can just start. HC is a productivity app
(a Telegram bot, with a web app coming), not a clinic.

## Voice

- Warm, plain, a little informal. Second person ("you"), with the author's first person where the
  author supplies a real experience.
- One idea per post and **one thing to do today**. If a draft has two tips, it is two posts.
- Short words. "Use", not "utilise"; "start", not "commence". Leonid flags words like
  "amalgamation" and named-principle jargon ("the Aaronson principle"): if a reader might stop on a
  word, swap it.
- Name the behaviour and what helps. Never the deficit.

## Respect: no deficit or clinical framing

Not: "ADHD symptoms", "suffer from", "disorder", "sufferers", "patients", "deficits",
"impairment", "broken brain", "normal people".
Instead: what people do and notice ("you lose track of time when something grabs you"), "many ADHD
adults", "people with ADHD". The disclaimer footer is the one place a clinical page is linked.
If a keyword itself contains a deficit word (for example "time blindness symptoms"), do not target it.

## Lived experience belongs to the author

Leonid's posts work because they say what happened to him. The writer must never invent that.
Where the post needs a personal example, leave a slot the author fills:

```
[AUTHOR: one sentence about a time hyperfocus landed on the wrong thing for you]
```

Write the surrounding text so it reads correctly once the slot is filled, and so the post still
makes sense if the author deletes the slot instead.

## Claims and sources

Rules from `docs/BLOG-STRATEGY.md` §5, which both founders agreed:

1. The model never invents a citation. A factual claim about ADHD or the brain either has a source the
   writer has opened, or is rephrased as experience ("many of us find…").
2. Every external link is opened and must say what the sentence says: title, year, population.
3. Prefer, in order: lived experience; reputable ADHD organisations as commentary; papers opened on
   PubMed / DOI; official UK health pages (NHS) for anything medical.
4. Never link a journal homepage as if it were a paper.
5. Never claim clinical outcomes for Herding Chickens.
6. If the evidence is thin, say so. "Research on hyperfocus is still thin" is a fine sentence.
7. A study that is not about ADHD can be cited, but the post says so.

The proof goes in the post's **sources ledger**, `<slug>.sources.json`, next to the draft:

```json
[
  {"url": "https://pubmed.ncbi.nlm.nih.gov/23688211/",
   "claim": "Adults with ADHD score lower on working-memory tests, on average, across 38 studies.",
   "passage": "yielded 38 studies of WM in adults with ADHD ... moderate-magnitude between-group effect sizes",
   "checked_on": "2026-11-13"}
]
```

`passage` is copied from the source, not paraphrased. A PubMed abstract can be fetched as plain text
with `curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=<PMID>&rettype=abstract&retmode=text"`.

## Links to us

- Every "let us know", "tell us", "get in touch" is a link to the contact page:
  `[let us know](/contact)` (the site's relative form) or `https://herdingchickens.com/contact`.
- One product invitation per post, after the tip: the bot (`https://t.me/HerdingChickensBot`) and/or
  updates (`/early-access`), in one paragraph. Say honestly what exists today (the Telegram bot)
  and what is coming.
- Internal links go to `/resources/<slug>`; the topic hub is `/resources/topics/<cluster>`.

## Post shape (what the site renders)

1. Opening: 2-4 sentences, a scene the reader recognises, then the keyword once in plain words.
2. `## The short version` then a ```short fence: 3-6 rows `Label | one or two sentences`, last row
   `Do this today | ...`.
3. Body: short sections, one of them a question heading answered in its first sentence.
4. The one thing to try, said plainly.
5. The product paragraph.
6. `## FAQ`: 2-4 `**Question?**` lines, each followed by a short answer paragraph.
7. `## Keep reading`: 2-4 related posts plus the cluster hub link.
8. `---` then the italic disclaimer footer (copy it from the template).

`{{area:<slug>}}` tokens render the app's coloured area squares; do not hard-code squares.

## Humanizer pass (last step before the report)

Use `ai-tells.md` (shared with the `humanizer` and `scientific-humanizer` skills) and
`plain-strong-writing.md`, in a casual blog register rather than a scientific one:

- strip AI vocabulary, puffery and "not X but Y" constructions;
- at most one em-dash, and at most **one idiom** in the whole post;
- vary sentence length; avoid a run of identical short sentences;
- no closing moral, no "In conclusion", no rhetorical question chains;
- read it aloud. If a sentence would sound odd said to a friend, rewrite it.
