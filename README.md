# Research agent skills

Seven skills for writing and checking scientific papers with Claude Code. They also work in
Codex (see "Installing in Codex"), where only the Illustrator has been tested.

| Skill | What it does |
|---|---|
| `scientific-humanizer` | Rewrites scientific prose so it reads as if a careful scientist wrote it, keeping every number, symbol, citation and claim strength, and flags claims whose strength looks wrong |
| `formatter` | Compiles a private copy of a LaTeX or pandoc Markdown manuscript and checks its layout and structure: split tables, empty space, long paragraphs, undefined terms, section transitions, the paragraph describing how the paper is organised |
| `referencer` | Checks each citation against the full text of the cited work, records the exact supporting passage, and builds a web page showing each claim beside its source |
| `lit-reviewer` | Reviews the literature around a project and builds a web page of related work, colour-coded by how much it overlaps the project |
| `peer-reviewer` | Writes a referee report on a manuscript, judging the methods first and the presentation second |
| `illustrator` | Creates static figures for a manuscript's main results, with scripts that regenerate them |
| `demonstrator` | Builds an animated step-by-step demonstration of a method on a small example |

## Installing in Claude Code

Claude Code loads every skill it finds as a folder in `~/.claude/skills/`. Clone this
repository and link each skill folder into that directory:

```sh
git clone https://github.com/Leonardini/ResearchAgent.git
cd ResearchAgent
mkdir -p ~/.claude/skills
for s in demonstrator formatter illustrator lit-reviewer peer-reviewer referencer scientific-humanizer; do
  ln -s "$PWD/$s" ~/.claude/skills/$s
done
```

Start a new Claude Code session. You can then ask for a skill by name ("run the formatter on
paper.tex") or with a slash command, for example
`/illustrator Create figures for the salient results in my manuscript.` Claude will also pick
a skill up when a request matches its description. To install only some of the skills, list
just those in the loop.

**For one project only**, link into that project's `.claude/skills/` folder instead of
`~/.claude/skills/`. From the project's root (replace `/path/to/ResearchAgent` with where you
cloned it):

```sh
mkdir -p .claude/skills
ln -s /path/to/ResearchAgent/illustrator .claude/skills/illustrator
```

**Use links, not copies.** `scientific-humanizer/references/` links to the writing guides in
`shared/`, and a copied folder loses them. Keep the clone where it is: the links point into it.
To update, run `git pull` in the clone. The links pick up the change.

**On Windows**, git checks symbolic links out as plain text files unless symlinks are enabled.
Use WSL, or clone with `git clone -c core.symlinks=true` from a terminal that is allowed to create
symlinks.

## Installing in Codex

Codex reads workspace skills from `.agents/skills/` and follows symbolic links
([Codex documentation](https://learn.chatgpt.com/docs/build-skills)). From the workspace's root
(replace `/path/to/ResearchAgent` with where you cloned it):

```sh
mkdir -p .agents/skills
ln -s /path/to/ResearchAgent/illustrator .agents/skills/illustrator
```

Restart Codex if the skill does not appear. In Codex a skill is invoked with `$`, not `/`:

```
$illustrator Create figures for the salient results in my manuscript.
```

The link keeps the installed skill in step with the clone, so `git pull` updates it. Only
`illustrator` has been used in Codex so far; it was built there and carries a Codex description
file (`agents/openai.yaml`). The other skills are linked the same way but rely on their
`SKILL.md` alone, and have not been tested in Codex.

## What each skill needs

All the helper scripts need Python 3. Beyond that:

| Skill | Needs |
|---|---|
| `formatter` | pandoc, latexmk (a TeX distribution) and the PyMuPDF Python package (`pip install pymupdf`) |
| `referencer` | `pdftotext` (from poppler); `ocrmypdf` only for scanned PDFs; network access to arXiv, OpenAlex, Europe PMC, Semantic Scholar and Crossref |
| `demonstrator` | Chrome or Chromium and ffmpeg, to export the animation as MP4 or GIF |
| `illustrator` | Matplotlib, for the figure scripts it writes |
| `lit-reviewer` | Network access to OpenAlex and arXiv; an OpenAlex API key (`OPENALEX_API_KEY`) is optional |
| `scientific-humanizer`, `peer-reviewer` | Nothing beyond Python |

Some skills use optional connectors (Undermind, Firecrawl) when they are available and work
without them.

## Before you rely on them

- **The Referencer's licence check needs the `papers` plugin from the co-scientist-toolkit.**
  With the plugin installed, the Referencer refuses to send the text of a subscription paper to
  the model. Without it the check is off and the report says so. Install the plugin if this
  matters for your institution's licences.
- **The Referencer's Unpaywall lookup sends your email address to Unpaywall**, and only runs if
  you set `UNPAYWALL_EMAIL`.
- **Some conventions are the author's own.** `scientific-humanizer/references/scientific-style.md`
  §5 lists manuscript conventions that the skill applies as "the user's", for example active
  voice, no imperative sentence openers and no foreshadowing of results. The Peer-reviewer's
  `references/style-guide.md` is drawn from its author's own referee reports. Edit both to match
  your own style.
- **The skills edit files.** The Formatter and the Scientific-humanizer change manuscripts in
  place, after saving a `*.before-*` copy when the file is not under git. Use them on a copy, or
  on a file tracked in git, until you know what they do.

## Repository layout

Each skill folder holds its `SKILL.md` (the instructions Claude follows), plus `references/`,
`scripts/` and `assets/` where it has them. `prompts/` contains the prompt each skill was first
built from, `shared/` the writing guides used by the Scientific-humanizer, and `tools/` a viewer
for evaluation results. Evaluations are not included, because their inputs contain unpublished
manuscripts and copyrighted papers. `AGENTS.md` has notes for agents working on the skills
themselves.
