# Answer-engine optimisation (AEO / GEO): what is credible, and what HC does with it

AEO (also called GEO, generative engine optimisation) means writing so that ChatGPT, Perplexity and
Google's AI Overviews quote the post when someone asks them a question. Most writing on the subject is
vendor marketing. This file keeps only what a primary source supports; the sources are in
`sources.md` with the date each was read.

## What the primary sources say

1. **Google: no special trick.** Google's page on AI features says there are "no additional
   requirements to appear in AI Overviews or AI Mode, nor other special optimizations necessary", and
   "no special schema.org structured data that you need to add". A page must be indexed and eligible
   for a snippet. Ordinary good practice applies: crawlable, internally linked, important content in
   text. [S1]
2. **Google: no preferred word count.** Its helpful-content guidance lists "writing to a particular
   word count because you've heard … Google has a preferred word count" as a warning sign. "(No, we
   don't.)" It also asks for first-hand experience, clear authorship, and disclosure where AI
   substantially wrote the content. [S2]
3. **FAQ rich results are mostly gone, the markup is harmless.** Since August 2023 Google shows FAQ
   rich results only for well-known government and health sites; there is "no need to proactively
   remove" FAQPage markup. [S3] So an FAQ block earns its place by giving answer engines clean
   question-and-answer pairs, not by a Google snippet.
4. **ChatGPT search needs its crawler let in.** "Sites that are opted out of OAI-SearchBot will not be
   shown in ChatGPT search answers." [S4]
5. **The GEO study.** Aggarwal et al. (KDD 2024) rewrote web pages in nine ways and measured how much of
   each page a generative engine used. Adding quotations, statistics and cited sources did best, with
   gains of up to 40%; fluent, easy-to-read text also helped; keyword stuffing scored *below* the
   untouched page. Effects varied by domain. [S5] This is one benchmark study, on its own engine
   set-up, so treat it as direction, not as a law.

## What HC does with it (rules in `../rules.toml`)

| Rule | What it asks | Basis |
|---|---|---|
| `short_version_early` | The direct answer, as the ```short block, within the first ~250 words | Answer-first; also BLOG-STRATEGY's TL;DR |
| `keyword_in_opening` | Name the thing plainly in the opening lines, so a quoted passage is self-explanatory | [S1], [S5] fluency |
| `question_heading` | At least one `## ` heading phrased as the question people type ("What is ADHD hyperfocus?") with the answer in its first sentence | Common AEO practice; low cost |
| `faq_block` | `## FAQ` with 2-4 `**Question?**` + short answer pairs; the site emits FAQPage JSON-LD from it automatically (`parseFaqFromContent` in `lib/blog/index.ts`) | [S3], answer engines lift Q&A pairs |
| `faq_answers_standalone` | Each answer under 60 words and starting with the subject, not "It" | A quoted answer has no surrounding context |
| `no_keyword_stuffing` | Keyword at most ~1.5 times per 100 words | [S5] |
| `statistics_or_named_source` | **Off by default.** At least one verified named source | [S5] supports it; fabrication risk keeps it off |
| `ai_crawlers_allowed` | Site-level: robots.txt admits Googlebot, OAI-SearchBot, PerplexityBot | [S1], [S4] |

Things deliberately **not** done: per-post `llms.txt` entries or extra schema (Google says none is
needed; the site already has an `llms.txt` and emits Article, Breadcrumb and FAQPage JSON-LD), and
inflating posts with statistics for their own sake.

## How a question heading should read

Use the searcher's own words, and answer in the first sentence under it, naming the subject:

```
## What is ADHD hyperfocus?

ADHD hyperfocus is a state of deep absorption in one task, so complete that ...
```

Not "## Understanding the hyperfocus phenomenon".
