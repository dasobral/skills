# Orchestration Plan

**Date**: 2026-03-13
**Task**: Analyse the technical document `architecture.md` and produce an executive summary report
**Agent pool**: `examples/agents/`

---

## 1. Agent Registry

| ID | Name | Role | Input contract | Output contract |
|----|------|------|---------------|----------------|
| A1 | `reader` | Document section extractor | Raw document text (file path or inline content) | JSON array of `{title, level, content, word_count}` objects |
| A2 | `analyzer` | Technical document analyst | JSON sections array from reader | Markdown report with ## Summary, ## Findings, ## Risks, ## Recommendations, ## Metrics |
| A3 | `report-writer` | Executive report author | Markdown analysis report from analyzer | Polished Markdown executive summary (400–800 words prose) |

---

## 2. Task Decomposition

| ID | Description | Inputs required | Expected output | Dependencies |
|----|-------------|----------------|----------------|-------------|
| T1 | Read the document and extract structured sections | `examples/input/architecture.md` (raw file) | `doc_sections` — JSON array of section objects | — |
| T2 | Analyse sections for findings, risks, and recommendations | `doc_sections` (T1 output) | `analysis_report` — Markdown with Findings, Risks, Recommendations, Metrics | T1 |
| T3 | Write an executive summary report from the analysis | `analysis_report` (T2 output) | `final_report.md` — polished Markdown executive summary | T2 |

---

## 3. Agent Assignments

| Subtask | Assigned Agent | Rationale |
|---------|---------------|-----------|
| T1 — Read document | A1: `reader` | Role matches exactly; input is raw document; output is structured sections |
| T2 — Analyse sections | A2: `analyzer` | Input contract matches T1 output (JSON sections); output is Markdown analysis |
| T3 — Write report | A3: `report-writer` | Input contract matches T2 output (Markdown analysis); produces final deliverable |

---

## 4. Task Graph (ASCII DAG)

```
[T1: reader] ──→ [T2: analyzer] ──→ [T3: report-writer] ──→ FINAL OUTPUT
```

**Legend**: `[Tn: agent-name]` — subtask node  ·  `──→` sequential dependency

---

## 5. Execution Sequencing

| Phase | Subtasks | Mode | Reason |
|-------|----------|------|--------|
| Phase 1 | T1 | sequential | No dependencies; must run first to provide input for T2 |
| Phase 2 | T2 | sequential | Depends on T1 output; cannot start until T1 completes |
| Phase 3 | T3 | sequential | Depends on T2 output; cannot start until T2 completes |

*Note: This is a linear pipeline — no parallelism opportunity. All three
subtasks are strictly sequential.*

---

## 6. Data Handoff Contracts

| From | To | Artifact name | Format | Required fields / schema |
|------|----|--------------|--------|--------------------------|
| T1 | T2 | `doc_sections` | JSON array (fenced code block) | `[{title: string, level: int, content: string, word_count: int}]` — all fields required |
| T2 | T3 | `analysis_report` | Markdown document (plain text) | Must contain `## Summary`, `## Findings`, `## Risks`, `## Recommendations`, `## Metrics` sections |

---

## 7. Failure Policy

| Subtask | On transient error | On contract violation | On persistent failure |
|---------|-------------------|-----------------------|----------------------|
| T1 | Retry up to 2× | Re-invoke with explicit JSON schema in prompt | Halt pipeline; escalate — no document = nothing to analyse |
| T2 | Retry up to 2× | Re-invoke with explicit section headers requirement | Halt T3; escalate with T1 output preserved |
| T3 | Retry up to 2× | Re-invoke with explicit report structure and word-count constraint | Escalate with T2 output as fallback deliverable |

---

## 8. Output Specification

**Terminal subtask(s)**: T3

**Final deliverable**: Executive summary Markdown report (`final_report.md`)

**Output path**: `examples/output/final_report.md`
