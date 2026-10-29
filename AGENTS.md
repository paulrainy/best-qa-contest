# Repository Guidelines

## Project Structure & Module Organization

This repository develops materials for the 2026–2027 “Best Tester” contest, including deliberately defective exercises and supporting software.

- `rating-tasks.md`: rating-stage tasks and evaluation criteria.
- `review-tasks/1a–1d-*`: review exercises, each separating `participant/` deliverables from `jury/` answer keys, scoring sheets, and corrected examples.
- `review-tasks/tools/`: Python artifact generators and their `test_*.py` tests.
- `final-task/`: transfer-service case; participant specifications, stand launchers, and Java/Python starters; jury stand sources and verification scripts.
- `base-docs/`, `previous-year/`, and `docs/superpowers/`: reference materials, historical examples, and design plans.

Consult the relevant task README before editing. `CLAUDE.md` contains early planning assumptions; current task READMEs describe the implemented tooling.

## Build, Test, and Development Commands

Run from the repository root unless specified:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r review-tasks/tools/requirements.txt
python -m pytest review-tasks/tools
```

These commands install generator dependencies and run their tests.

From `review-tasks/tools/`:

- `python build_testcases.py ../1b-testcase-review`: regenerate participant and corrected spreadsheets from Markdown sources.
- `python build_sheets.py ../1b-testcase-review`: validate the answer key and regenerate answer/scoring sheets; substitute another exercise directory as needed.

For the final stand, run `bash final-task/jury/build-stand.sh` (JDK 17+ with `jmods`, Maven), then `bash final-task/participant/stand/run.sh`. See `final-task/README.md` for verification commands, which reset stand data.

## Coding Style & Naming Conventions

Keep contest prose in Russian and preserve existing identifiers, relative links, and task numbering. Follow adjacent code: four-space indentation, Python `snake_case`, and Java `PascalCase` classes. No repository-wide formatter or linter is configured. Edit `jury/source/` inputs and regenerate derived spreadsheets/documents rather than editing those outputs directly.

## Testing Guidelines

Use pytest tests named `test_*.py` for generator changes; no coverage threshold is documented. Check generated artifacts visually and keep answer-key references synchronized after code edits. Preserve seeded defects and valid-code traps unless explicitly changing the exercise; participant examples are intentionally imperfect.

## Commit & Pull Request Guidelines

History uses scoped prefixes such as `feat(final):`, `fix(1a):`, and `docs(1c):`, usually with Russian descriptions. Keep commits focused. PRs should identify affected exercises, explain scoring or participant-facing changes, and report validation. Include linked issues when applicable and previews for layout changes.

Package only `participant/` materials. Exclude jury keys, stand sources, caches, local environments, and build intermediates; follow each README’s packaging instructions.
