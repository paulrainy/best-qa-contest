# Repository Guidelines

## Project Structure & Module Organization

This repository develops materials for the 2026–2027 “Best Tester” contest, including deliberately defective exercises and supporting software.

- `rating-tasks.md`: rating-stage tasks and evaluation criteria.
- `review-tasks/1a–1d-*`: review exercises, each separating `participant/` deliverables from `jury/` answer keys, scoring sheets, and corrected examples.
- `review-tasks/tools/`: Python artifact generators and their `test_*.py` tests.
- `final-task/`: transfer-service case; participant specifications, stand launchers, and Java/Python starters; jury stand sources and verification scripts.
- `docs/base-docs/`: original chat export and organiser presentations; use `rating-tasks.md` where they disagree.
- `docs/superpowers/specs/` and `docs/superpowers/plans/`: dated design specifications and implementation plans.
- `previous-year/`: historical examples for reference.

Consult the relevant task README before editing. `CLAUDE.md` is the fuller guide (map, invariants of the exercises, commands); task READMEs describe the implemented tooling in detail.

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
- For 1c protocols, run `python ../1c-load-review/jury/source/protocols/charts.py 11 12 13 14 15`, then the same command with `--check`, then `python build_protocols.py ../1c-load-review`, and finally `python build_sheets.py ../1c-load-review`.

The 1c participant folders are `1-scripts/`, `2-protocols/`, and `3-monitoring/`. Bundled JMeter 5.6.3 and Java 17 are under `participant/1-scripts/tools/`; binaries use Git LFS. Set absolute `JMETER_HOME` and `JAVA` paths to enable real JMeter checks in the generator tests or `build_jmx.py --check`. See `review-tasks/README.md` for the full generation pipeline and platform-specific paths.

For the final stand, run `bash final-task/jury/build-stand.sh` (JDK 17+ with `jmods`, Maven), then `bash final-task/participant/stand/run.sh`. See `final-task/README.md` for verification commands, which reset stand data.

## Coding Style & Naming Conventions

Keep contest prose in Russian and preserve existing identifiers, relative links, and task numbering. Follow adjacent code: four-space indentation, Python `snake_case`, and Java `PascalCase` classes. No repository-wide formatter or linter is configured. Edit `jury/source/` inputs and regenerate derived spreadsheets/documents rather than editing those outputs directly.

Each review exercise has exactly 20 units with 5 seeded defects each, plus 10 valid-code/text traps. Preserve this contract when correcting unintended errors. `jury/answer-key.md` is machine-parsed and defines scoring: keep its table structure and references synchronized with the material, then regenerate both spreadsheets. Shared helpers, requirements, and methodology are defect-free by contract.

## Testing Guidelines

Use pytest tests named `test_*.py` for generator changes; no coverage threshold is documented. Check generated artifacts visually and keep answer-key references synchronized after code edits. Preserve seeded defects and valid-code traps unless explicitly changing the exercise; participant examples are intentionally imperfect.

For 1c protocols, verify Markdown tables against chart data and generated DOCX content. Total p95 must come from the complete sample set, not from averaging window percentiles. Inspect DOCX pagination in Word, including repeated table headers, row splits, and placement of figures and captions; source/XML checks alone do not establish visual correctness. Static checks and local stubs can validate the exercise without an EFR stand, but cannot establish real-system performance or acceptance results.

## Commit & Pull Request Guidelines

History uses scoped prefixes such as `feat(final):`, `fix(1a):`, and `docs(1c):`, usually with Russian descriptions. Keep commits focused. PRs should identify affected exercises, explain scoring or participant-facing changes, and report validation. Include linked issues when applicable and previews for layout changes.

Package only `participant/` materials. Exclude jury keys, stand sources, caches, local environments, and build intermediates; follow each README’s packaging instructions.
