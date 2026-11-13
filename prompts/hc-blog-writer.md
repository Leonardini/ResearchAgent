# HC blog writer — original brief

Given 2026-11-13 (relayed by the coordinating agent), summarised:

---

Build a skill, `hc-blog-writer`, that writes blog posts for the HerdingChickens website meeting SEO
and AEO criteria (being quoted by ChatGPT, Perplexity and Google AI Overviews). Stéphane will iterate
on it, so it must be easy to read and change.

- Follow Connor Gillivan's "My Perfect SEO Blog Checklist", which Stéphane wants, but with Leonid's
  stance of 22 Aug 2026: the maximalist items (1,500+ words, 5+ images, table of contents, embedded
  video, expert quotes, several CTA types) conflict with HC's design principle of bite-sized posts,
  one actionable tip each, written for ADHD readers who are easily overwhelmed. Items that do not
  conflict with brevity (title, keyword placement, meta description, alt text, links, readability,
  mobile) stay. **Make each checklist item a named, switchable rule with a one-line reason**, marking
  which are on and off by default: that is the dial the founders will argue over.
- Keywords: Stéphane's Ubersuggest position-tracking export (CSV: Keyword, Position, Change, Search
  Intent, Volume, SEO Difficulty, URL); the skill reads that format directly. Skip keywords an existing
  post already targets; merge near-duplicates.
- Voice and format: Leonid's posts in the website repo's `content/blog/` (read-only).
- Research current AEO/GEO guidance briefly and cite the sources.
- House rules: no deficit or clinical framing of ADHD; small words; every "let us know" / "tell us"
  links to https://herdingchickens.com/contact; no fabricated citations, with a verification step and
  a link check; a humanizer pass in a casual register with at most one idiom.
- Output: a Markdown post in the site's frontmatter format, `published: false`, plus a checklist
  report showing which rules passed, failed or were switched off.
- Test it on 3 to 5 posts for keywords at the top of the 30 Oct 2026 export.

## Design decisions

- **One rule register, `rules.toml`.** Every rule's switch, numbers and reason live there; the
  checker reads it, and fails loudly if a rule and a check fall out of step. Off rules are still
  reported, with what their result would have been.
- **Replacements, not just removals.** Where a Gillivan item is off, a smaller house rule takes its
  place: word count by tier, three internal links (one in the body), every external link verified.
- **The sources ledger is the citation gate.** Each external link needs an entry with the passage
  copied from the source. `--check-links` fetches links, and checks PubMed and PMC IDs through
  E-utilities, because those sites answer a made-up ID with a normal-looking page.
- **The author's experience is never invented.** Drafts carry `[AUTHOR: ...]` slots, reported as open.
- **AEO from primary sources only**: Google's AI-features and helpful-content pages, the 2023 FAQ
  rich-result change, OpenAI's crawler page and the GEO paper (KDD 2024). Vendor guides were not used.
