# AI writing tells — full reference

Distilled from Wikipedia's *[Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)*,
scoped to **general prose** (the wiki-specific plumbing — citation-markup bugs, edit summaries,
wikitext, AfC drafts, category/template calls — is dropped because it doesn't apply to text a user
pastes in). Use this to recognize tells; use SKILL.md's contract and method to fix them.

**Contents**
1. Vocabulary that spiked by model era
2. Content-level tells (with examples)
3. Cadence & symmetry tells
4. Typography & formatting tells
5. Occasionally-relevant meta tells
6. What is *not* a reliable tell

---

## 1. Vocabulary that spiked by model era

Presence of one of these is weak evidence on its own — density is what matters. Don't blanket-ban
them; a single natural "crucial" is fine.

**2023–mid-2024 (GPT-4 era):** additionally, boasts, bolstered, crucial, delve, emphasizing,
enduring, garner, intricate / intricacies, interplay, key, landscape, meticulous / meticulously,
pivotal, underscore, tapestry, testament, valuable, vibrant.

**Mid-2024–mid-2025 (GPT-4o era):** align with, bolstered, crucial, emphasizing, enhance, enduring,
fostering, highlighting, pivotal, showcasing, underscore, vibrant.

**Mid-2025+ (GPT-5 era):** emphasizing, enhance, highlighting, showcasing.

**Grok-flavored:** causal, empirical, correlate, underscore.

**Claude-flavored:** **load-bearing** (metaphorical). Outside structural engineering — a load-bearing
wall, a load-bearing beam — this is a strong and specific Claude tell, and readers who know the model
recognise it on sight. It attaches to claims, assumptions, sentences, citations, details: "the
load-bearing claim", "that adjective is load-bearing". Nothing is wrong with the metaphor; the
problem is that Claude reaches for it constantly, so its density is diagnostic even when any single
use reads fine. **Fix by naming what the thing actually does**, which is almost always more precise:
*the claim the argument rests on* · *the step that has to hold* · *the assumption doing the work* ·
*foundational* · *the critical one*. If none of those fit, the sentence probably did not need the
emphasis at all.

Related favorites seen across models: realm, foster, leverage, robust, seamless, spearhead, navigate
(used metaphorically), commitment to, groundbreaking, renowned, diverse array, rich, profound.

---

## 2. Content-level tells

**Undue emphasis on significance / legacy** — inflating a mundane subject's importance:
"stands / serves as", "is a testament / reminder", "plays a crucial / pivotal / vital / key role",
"underscores / highlights its importance", "reflects broader", "symbolizing its ongoing / enduring /
lasting", "setting the stage for", "marking / shaping the", "represents a shift", "key turning
point", "evolving landscape", "focal point", "indelible mark", "deeply rooted".
> *e.g. a small town's name change "highlighting the enduring legacy of the community's resistance."*

**Superficial analysis via present participles** — vacuous commentary tacked on, often synthesis:
"highlighting / underscoring / emphasizing", "ensuring", "reflecting / symbolizing", "contributing
to", "cultivating / fostering", "encompassing", "enhancing", "valuable insights", "align / resonate
with".
> *e.g. "…has supported various services, contributing to the socio-economic development of the region."*

**Promotional / travel-guide tone** — "boasts a", "vibrant", "rich", "nestled", "in the heart of",
"natural beauty", "groundbreaking", "renowned", "featuring", "diverse array", "commitment to".
> *e.g. "Nestled within the breathtaking region of Gonder, Alamata Raya Kobo stands as a vibrant town."*

**Vague attribution / overgeneralization** — opinions pinned on undefined authorities, or source
count exaggerated: "Industry reports", "Observers have cited", "Experts argue", "Some critics
argue", "several sources / publications" (when few or none are cited), "such as" before an
exhaustive list. **Do not resolve these by inventing a source** — name the real one or cut the claim.

**Outline-like conclusion** — the formula "Despite [positives], [subject] faces challenges" then
vague future speculation: "Despite its…", "faces several challenges", "Despite these challenges",
"Challenges and Legacy", "Future Outlook", "Looking ahead", "In conclusion".

**Copula avoidance** — dodging plain "is/are": "serves as / stands as / marks / functions as /
operates as / represents", "boasts / features / maintains / offers", "refers to".
> *e.g. "Gallery 825 is LAAA's exhibition arm" rewritten as "…serves as LAAA's exhibition space."*

---

## 3. Cadence & symmetry tells

**Negative parallelism**, three shapes:
- "Not only… but (also)" / "It is not just…, it's" — implies correcting an incomplete thought.
  > *"This is not only a work of self-representation, but a visual document of her obsessions."*
- "Not X, but Y" / "no…, no…, just" — denies the first thing to elevate the second.
  > *"This is not a mirror but a portal: not a representation of self, but a mechanism for reinvention."*
- "X rather than Y" — the reversal (common in Grok output).
  > *"prioritizing empirical consolidation of power… rather than ideological purity."*

Fix: state the positive claim directly. Most of the time you can drop the negated half entirely.

**Rule of three** — triplet adjectives, triplet phrases joined with "and", or three parallel list
items, used for a false sense of completeness. Keep the items that carry distinct meaning; three
genuinely-distinct things is not a tell.

**Elegant variation / lexical churn** — repetition-penalty artifacts: swapping in synonyms
("Soviet artistic constraints" → "non-conformist artists" → "their creativity") instead of repeating
the core term, which makes the reader work to see they're the same thing. Prefer repeating the term.

---

## 4. Typography & formatting tells

- **Em-dash overuse** — the single most common surface tell. Reduce with commas, periods,
  parentheses. Don't zero it out; humans use em-dashes.
- **Title Case In Headings** → sentence case ("Impact of technology", not "Impact of Technology").
- **Boldface overuse** — mechanically bolding every instance of a chosen term. Keep bold for genuine
  emphasis only.
- **Inline-header vertical lists** — bullets/numbers with a **bolded label:** then a colon and a
  sentence, repeated. Often prose that was chopped into a list. Restore to prose if the items are
  really sentences.
- **Emoji as bullets or decorative separators** → remove.
- **Curly “quotes”/apostrophes** → straight `'` `"`.
- **`---` thematic breaks before every heading**, and **skipped heading levels** (H2 → H4) → normalize.
- **Markdown when the destination is plain text** — `**bold**`, `# header` where none was wanted.

---

## 5. Occasionally-relevant meta tells

Mostly wiki-specific, but two show up in pasted general text:

- **Knowledge-cutoff disclaimers** — "As of my last update…", "I don't have information beyond…",
  spontaneous speculation about gaps in the source. Always cut — a human author wouldn't write these.
- **Collaborative / assistant phrasing** — "Certainly! Here's…", "I hope this helps", "Let me know
  if…", "Sure, here is the rewritten version." Cut; it's the chatbot frame, not the content.

---

## 6. What is *not* a reliable tell (avoid false positives)

The source guide is explicit that these, **alone**, do not prove AI authorship — so don't mangle good
writing chasing them:

- Any single "AI vocabulary" word used naturally.
- Promotional language on its own (some subjects really are notable).
- A vague attribution in isolation (some claims genuinely lack a nameable source).
- Ordinary grammatical imperfection.

The real target is the **cluster** — several tells co-occurring, plus the underlying moves
(inflated significance, empty analysis, false symmetry). Fix the cluster; leave clean prose alone.
