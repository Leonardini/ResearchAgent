# Repository Guidelines

## Project Structure & Module Organization

This repository contains seven research skills: `demonstrator/`, `formatter/`, `illustrator/`, `lit-reviewer/`, `peer-reviewer/`, `referencer/`, and `scientific-humanizer/`. Each defines its workflow in `SKILL.md`; supporting material lives in `references/`, Python helpers in `scripts/`, and templates in `assets/` where applicable. `illustrator/agents/openai.yaml` describes the Illustrator skill to Codex.

`prompts/` contains the prompt each skill was first built from, `shared/` contains common writing references, and `tools/review_viewer.py` supports reviewing evaluation results.

Evaluations are not part of this repository, because their inputs include unpublished manuscripts and copyrighted papers. Locally, scenario definitions live in each skill's `evals/evals.json`, with input fixtures under `evals/files/`, and the matching `*-workspace/iteration-*/` directories hold evaluation inputs, outputs, feedback, and benchmarks.

## Build, Test, and Development Commands

There is no root build command or centralized test runner. Run helpers from the repository root:

- `python3 lit-reviewer/scripts/litreview.py --help` — inspect literature-review commands.
- `python3 formatter/scripts/formatter.py --help` — inspect formatting operations.
- `python3 scientific-humanizer/scripts/check_preservation.py original.md revised.md` — verify that edits preserve mathematical expressions, citations, numbers, references, URLs, and code.
- `sh shared/check_shared.sh` — check shared-reference symlinks. This also checks `$HOME/.claude/skills/humanizer`, so failures can reflect local installation state.

Consult the relevant `SKILL.md` for workflow commands and external dependencies.

## Coding Style & Naming Conventions

Follow existing Python style: four-space indentation, `snake_case` functions and variables, and uppercase constants. Keep skill directories lowercase with hyphens. Use concise Markdown headings and actionable instructions. Preserve existing JSON formatting when editing evaluation definitions.

Edit common writing guidance in `shared/`; preserve the symlinks in `scientific-humanizer/references/`.

## Testing Guidelines

Evaluations are scenario-based, with prompts, expected outputs, and assertions in `evals/evals.json` (kept locally, see above). No centralized coverage threshold is defined. For behavior changes, run the affected helper and exercise a relevant scenario on copied inputs. Record outputs and assertion results in a new workspace iteration; preserve previous comparisons. Check generated HTML or LaTeX visually when presentation changes.

## Commit & Pull Request Guidelines

Use concise, imperative subjects such as `Fix referencer citation matching`. Keep changes focused on one skill or shared concern. Pull requests should explain the behavior change, identify affected skills, report validation, and include screenshots for visual changes. Link related issues when available.
