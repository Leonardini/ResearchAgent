# Connor Gillivan's SEO checklist, and what HC does with each item

Source: Connor Gillivan, "My Perfect SEO Blog Checklist" (newsletter, read 13 Nov 2026 at
https://connorgillivan.beehiiv.com/p/my-perfect-seo-blog-checklist; the same list was posted on
LinkedIn). Stéphane asked for it to be followed. Leonid's position (22 Aug 2026): keep every item
that does not make a post longer or busier, and switch off the maximalist ones, because HC posts are
bite-sized, one actionable tip each, written for readers who are easily overwhelmed.

Each item below maps to one or more named rules in `../rules.toml`. The switch and the one-line reason
live there; this file explains the mapping. To change the policy, edit `rules.toml`, not this file.

| # | Gillivan's item (paraphrased) | Rule(s) | Default | Why |
|---|---|---|---|---|
| 1 | Title has the keyword, modelled on the top results, not clickbait | `title_has_keyword`, `title_length`, `title_not_clickbait` | on | Costs nothing in length |
| 2 | Short, keyword-focused URL | `slug_short_keyword` | on | Costs nothing |
| 3 | Author bio for E-E-A-T, linked to an author page | `author_bio` | on | The site already has author pages; the post only names a known author |
| 4 | 1,500+ words, matched to what ranks | `word_count_1500` | **off** | Conflicts with bite-sized posts. Google: "no preferred word count". Replaced by `word_count_in_tier` |
| 5a | 5+ images | `images_5plus` | **off** | Turns a two-minute read into a scroll |
| 5b | Video or infographic | `video_or_infographic` | **off** | Load time and a second thing to attend to |
| 5c | Descriptive alt text | `cover_alt_text`, `inline_image_alt` | on | One line each |
| 7a | Table of contents | `table_of_contents` | **off** | A short post needs none; "The short version" does the job |
| 7b | Keyword in H1/H2/H3 | `keyword_in_h2` | on | One natural heading |
| 7c | Paragraphs of 1-2 sentences | `short_paragraphs` | on, relaxed to 4 | Leonid's voice runs a little longer |
| 7d | Bullets and numbered lists | `lists_where_helpful` | on | The short block is the list |
| 7e | Font and colour (#333, Poppins) | `font_and_design` | site | Set once in the site CSS |
| 8a | 5 internal links | `internal_links_5` | **off** | Too many exits mid-tip. Replaced by `internal_links_min` (3, one in the body) |
| 8b | 3+ external high-authority links | `external_links_3` | **off** | Each is a fabrication risk. Replaced by `sources_verified` (every link checked) |
| 9 | Mobile-friendly and fast | `mobile_and_speed` | site | Checked once for the site with PageSpeed Insights |
| 10a | Decide the one action you want | `one_cta` | on | One invitation, after the tip |
| 10b | CTAs in-content, sidebar and exit pop-up | `multiple_cta_types` | **off** | The overwhelm HC exists to remove |
| 11a | Expert quotes | `expert_quotes` | **off** | Length and fabrication risk; switch on per post with a real quote |
| 11b | Personal anecdotes and real examples | `lived_experience` | on | The author supplies them; the writer never invents them |
| 12 | Social share buttons | `social_share` | site | Site chrome |
| 13 | "Could this be better?" final edit | `final_edit` | on | The humanizer pass and a read-aloud |
| - | Meta description (asked for alongside the list) | `meta_description` | on | 120-160 characters, keyword, one outcome |
| - | Keyword early, not stuffed | `keyword_in_opening`, `no_keyword_stuffing` | on | See `aeo.md` on keyword stuffing |

The source numbers its sections 1 to 13 but has no item 6; the numbering above follows it.

## The argument to have

The off rules are the dial. Two of them have evidence on Stéphane's side that is worth weighing
rather than dismissing:

- **Expert quotes** (`expert_quotes`) and **statistics** (`statistics_or_named_source`): in the GEO
  study (`aeo.md`), adding quotations and statistics were the two methods that most raised a page's
  visibility in AI answers. They stay off by default because the pressure to add them is how fake
  studies got into earlier HC drafts. Switching them on for a post that has a real, verified quote or
  number costs little.
- **Word count**: the 1,500-word figure is about matching what already ranks for a keyword. Google says
  it has no preferred length, and answer engines lift short self-contained passages, so this one has
  the least support.
