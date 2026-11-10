# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Working repository for the jury of the **«Лучший тестировщик»** nomination of the RSHB-Интех contest «Лучший по профессии» 2026–2027. It holds the contest materials themselves: review exercises with **deliberately seeded defects**, their jury answer keys, Python generators that derive spreadsheets/documents from those keys, and a Java stand for the final case. Deadline for all jury deliverables: **31.10.2026** (internal 23.10.2026). Jury lead and sole author of tasks: Павел Колягин; disputed scoring goes to Марина Каприз.

All prose, identifiers in task material, commit messages and comments are in **Russian**. Keep it that way.

`AGENTS.md` is a shorter sibling of this file; keep the two consistent when changing conventions.

## Top-level map

| Path | What it is |
| --- | --- |
| `rating-tasks.md` | Decisions and open questions for the rating stage: checklists (autotests, manual cases, load report), rejected metrics, who scores |
| `review-tasks/README.md` | Hub for the four review exercises 1a–1d: what participants get, what is seeded, how scoring works, regeneration and packaging commands |
| `review-tasks/1a-autotest-review/` | Java autotest code review: 3 Maven sandboxes (`1-selenide`, `2-playwright`, `3-sql`) |
| `review-tasks/1b-testcase-review/` | Manual test-case review against three fictional BIQ requirements, plus a Java sandbox app |
| `review-tasks/1c-load-review/` | Load-testing material review: 10 JMeter scripts, 5 `.docx` protocols, 3 Grafana dashboards, 2 SQL scripts |
| `review-tasks/1d-python-review/` | Python autotest code review (pytest / Kafka / Playwright), run with `uv` |
| `review-tasks/tools/` | Generators and their pytest tests (see below) |
| `final-task/` | Final case «Сервис переводов»: four participant bundles + black-box stand, jury references, shared contract and stand sources |
| `docs/superpowers/specs/`, `docs/superpowers/plans/` | Dated design specs and implementation plans written before each piece of work; `2026-10-30-review-materials-followups.md` lists deferred proposals (1c part still pending) |
| `previous-year/` | Digests of last year's case, criteria and example artifacts; reference only |
| `docs/base-docs/` | Original chat export and organiser presentations; superseded by `rating-tasks.md` where they disagree |

Exercise numbering is Latin `1a`–`1d`; older specs/plans and commits still say `1а`/`1б`/`1г` (Cyrillic) — `1г` is today's `1c`.

## Core invariants of the review exercises

Every exercise 1a–1d follows the same contract, and the generators enforce it:

- **20 units × exactly 5 defects = 100 defects, plus exactly 10 traps** («ловушки» — correct-looking code/text that must *not* be reported). Score = `max(0, defects − 2 × traps)`, 0–100.
- **`jury/answer-key.md` is the single source of truth for scoring** and is *machine-parsed*: `build_sheets.py` reads rows matching `| Д<unit>.<n> | … |` / `| Л<n> | … |`, validates the counts above, checks that every referenced place (file:line, «Шаг 3», JMeter tree path, Grafana panel, SQL line) really exists in the material, and then writes `participant/answer-template.xlsx` and `jury/scoring-sheet.xlsx`. Do not hand-edit those xlsx files; do not change the key's table column layout without updating `build_sheets.py`. The column «Засчитываем, если…» is what a jury member matches against, so it must be judgeable without opening the code.
- **`participant/` is self-contained and is shipped as a zip**: nothing jury-only goes in there, links in `task.md` are relative within that folder. Jury material (keys, `fixed/`, `source/`, stand sources) stays under `jury/`.
- **Seeded defects and traps are the product.** Never "fix" a participant test, test case, script or protocol unless the task is explicitly to change the exercise, and then update `answer-key.md`, `jury/fixed/`, and regenerate. Shared code (helpers, `conftest.py`, common steps, BIQ, methodology) is defect-free by contract and participants are told so.
- **Derived files are generated from sources, never edited directly:**
  - 1b: `jury/source/testcases.md` → `participant/testcases.xlsx`; `jury/source/testcases-fixed.md` → `jury/fixed/testcases.xlsx` (`build_testcases.py`). `build_sheets.py` refuses to run if the xlsx is older than the source.
  - 1c: `jury/source/scripts/NN_*.py` → `.jmx` for participant and fixed (`build_jmx.py`, via `jmx.py`); `jury/source/protocols/NN-*.md` + `data_NN.py`/`charts.py` → `.docx` (`build_protocols.py`); `jury/source/monitoring/dashboards.py` → Grafana JSON. Only the fixed SQL in `jury/fixed/monitoring/` is hand-edited.
  - 1a/1d: tests are the source; only the two xlsx are generated.

## Commands

### Generators (`review-tasks/tools/`)

```bash
cd review-tasks/tools
python -m venv .venv && .venv/bin/pip install -r requirements.txt   # Windows: .venv\Scripts\pip
python -m pytest                      # all generator tests (~100; 2 skip without JMETER_HOME)
python -m pytest test_build_sheets.py -k 1b   # one file / one test
```

Regenerate after editing a key or source (run from `review-tasks/tools/`, argument is the exercise folder):

```bash
python build_sheets.py ../1a-autotest-review        # validate key, write answer-template + scoring-sheet (any of 1a–1d)
python build_sheets.py ../1c-load-review --partial  # places only, no xlsx — while a key is half-written
python build_sheets.py ../1b-testcase-review --show # print the text the key points at, for eyeballing
python build_testcases.py ../1b-testcase-review     # 1b xlsx exports from Markdown sources (run before build_sheets)
python build_jmx.py ../1c-load-review               # 1c JMeter scripts; add --check with JMETER_HOME set to load each .jmx in real JMeter 5.6.3
python build_protocols.py ../1c-load-review         # 1c protocols .docx (run charts.py first if chart data changed)
python build_monitoring_viewer.py ../1c-load-review # 1c offline review.html; rebuild after participant JSON/SQL changes
python build_monitoring_viewer.py ../1c-load-review --check # read-only freshness check before packaging
python build_wiki_html.py <path/to/task.md>         # HTML copy of a task statement for EvaWiki (output is not committed)
```

The full 1c pipeline order (data → dashboards → charts → protocols → sheets) is listed in `review-tasks/README.md`.

### Sandboxes participants run (useful to verify a change did not break them)

- 1a Java sandboxes: `mvn test` inside `1-selenide/`, `2-playwright/`, `3-sql/` (JDK 17+, Maven; `.mvn/maven.config` pins a local `.m2/` repo inside the project). Single test: `mvn test -Dtest=TK900105Test`. Headless: `-Dselenide.headless=true` / `-Dheadless=true`.
- 1b sandbox app: `mvn compile exec:java` in `participant/sandbox/` → `http://localhost:18081/efr/`; `mvn test` runs its JUnit suite. Port/date via `-Defr.port`, `-Defr.today`.
- 1d: `uv sync` then `uv run pytest` in `participant/python/` (Python 3.11 pinned by `.python-version`, versions locked in `uv.lock`; keep both committed).

### Final case (`final-task/`)

```bash
# Full JDK 17 (JAVA_HOME), jmods, Maven, Python 3.11+
bash final-task/jury/build-stand.sh
python3 final-task/jury/verify/check_distribution.py --check
bash final-task/1a-java/participant/stand/run.sh  # Java 17 or21, ports18400/5672/19400/19402
python3 final-task/jury/verify/verify_defects.py controls
python3 final-task/jury/verify/verify_defects.py
python3 -m unittest discover -s final-task/jury/tools
python3 -m unittest discover -s final-task/jury/verify
cd final-task/1a-java/jury/reference && mvn test
```

Verify scripts reset data. Ready JAR, runtime libraries and console ZIP are in each direction's `participant/stand/`, tracked via Git LFS. Build once, physically copy to four bundles. Run the same binaries on Java17/21. Sources stay in `jury/stand-src/`. Canonical contract: `jury/source/spec.md`; coverage: `jury/coverage-catalog.md`; provenance: `jury/stand-manifest.md`. Participant instructions are Markdown, no starters.

The final task builds testing from scratch. The user removed all deliberately seeded final-stand defects: F10/F16 are ordinary passing requirement checks, and accounting has no artificial delay or prefetch=1 restriction. Other seeded review-exercise quotas do not apply. Java/Python full reference runs must pass every registered testcase without failures, errors or skips; `jury/tools/check_reference_results.py` verifies the exact inventory and rejects every failure. Other reference directions require their own approved plans. Scoring comes after all four references.


## Workflow conventions

- Before extending an exercise, read its `jury/answer-key.md` «Как считаем» section and `review-tasks/README.md`; the scoring rules are deliberately identical across 1a–1d the final case has no current score scale until its four reference solutions are accepted.
- Larger changes start with a dated spec in `docs/superpowers/specs/` and a plan in `docs/superpowers/plans/` (format: `YYYY-MM-DD-<slug>-design.md` / `YYYY-MM-DD-<slug>.md`).
- Commits: `feat|fix|docs|chore(<scope>): <Russian summary>` where scope is `1a`…`1d`, `final`, `1a–1d`. Work goes on `feature/*` or `fix/*` branches merged via PR into `main`.
- Material is validated by "solving blind" with an LLM and by an independent colleague before release; record review-exercise results at the end of the answer key and final-reference results in the reference report. Known unverified items: Grafana import of 1c dashboards, performance thresholds of the final stand on VDI.
- Open decisions that affect scope live in «Открытые вопросы» of `rating-tasks.md`, `review-tasks/README.md` and `final-task/README.md` (notably: how to reconcile 0–100 review scores with 0–5 artifact scores, one vs two material variants, Java/Python availability on VDI). Check them before proposing new structure.
