# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is **not a software project** — there is no source code, build system, linter, or test suite. It is a working repository for designing tasks for the **«Лучший по профессии» 2026–2027** contest (RSHB-Интех / Экосистема / Автоматизация), specifically the **«Лучший тестировщик» (Best Tester)** nomination.

Contents:
- `base-docs/base-chat.md` — an exported chat log (in Russian) containing prior analysis and draft proposals for the tester nomination's tasks.
- `base-docs/base-presentation.pdf` — the 13-slide jury presentation describing the contest's overall structure, timeline, and rules.

All future work in this repo is expected to be **written material**: task specifications, evaluation rubrics/checklists, sample specs with seeded defects, jury scoring sheets, etc. — not code. Treat requests here as content-drafting tasks, not engineering tasks.

## Contest structure (from base-presentation.pdf)

- 8 nominations total; this repo only concerns **Лучший тестировщик**.
- Jury for the tester nomination: Олег Денисов, Сергей Жихарев, Марина Каприз, **Павел Колягин** (lead).
- Coordinator: Софья Егорова (egorovasd@intech.rshb.ru).
- Timeline: rating-task stage runs October 2026 – February 2027 → top 10 scorers advance to a semifinal (March, rules not yet defined) → final (April–May 2027, ~40 min slot per nomination, 7 min presentation + 3 min Q&A + 2 min scoring) → awards ceremony (June 2027).
- **Jury deliverable deadline: October 31, 2026** for both the rating-stage tasks and the final case.
- Draft slide 9 proposed "found/closed Jira defects" as the tester's rating metric — flagged in `base-chat.md` as a bad metric (gameable, depends on codebase/requirement quality rather than tester skill) and marked "requires clarification from jury experts," meaning it is expected to be replaced, not implemented as-is.

## Key open questions (from base-chat.md)

Before drafting new task material, check whether these have been resolved (e.g., in newer chat exports or jury communication) — they affect scope:
1. What exactly is the **semifinal**? It's on the timeline but has no defined rules, and the math doesn't reconcile (10 advance from rating stage, but final slots suggest 3–4).
2. Is there an **automation/load-testing sandbox environment** available? This gates whether specialization tracks for automation/load testing can be hands-on or must be reduced to code/report review exercises.
3. **Who scores submissions** — testers/jury experts, or non-expert organizers? This determines whether tasks must be scorable against a fixed answer key (no expert judgment required) or can rely on rubric-based expert review.

## Prior draft proposal (base-chat.md)

An existing draft (Russian) proposes:
- **Rating stage**: Block A (50 pts, common to all) — requirements analysis/test design on a seeded spec with ~12 planted defects, scored against an answer key; Block B (30 pts, choose one specialization track: automation / load / manual-exploratory / methodology); Block C (20 pts) — Jira bug-report quality audit (checklist-based, replacing the raw defect-count metric).
- **Final case**: "Утечка в прод" (prod incident) — finalists get an incident package 2 weeks ahead, present a root-cause/prevention analysis in 7 minutes against a 5-criterion/25-point rubric. Fallback case: "deadline cut from 10 days to 3" (risk-based test scoping).

When asked to extend or revise this material, treat the above as the current baseline, not a finished decision — the chat log ends with an open question about which block to develop next.
