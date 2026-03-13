---
name: cpp-realtime-reviewer
description: >
  Reviews production C++ code for real-time embedded and networked systems —
  targeting senior engineers working on cryptography, QKD/QRNG, and secure
  satellite-ground communication. Checks thread safety, mutex/atomic/condvar
  correctness, RAII and resource ownership, latency bottlenecks and blocking
  calls in hot paths, and concurrency-safe logging patterns.
  Produces a structured report with CRITICAL / WARNING / SUGGESTION severity
  tags, inline-annotated code snippets, and a summary scorecard.
  TRIGGER when the user asks to "review this C++ code", "check for race
  conditions", "audit thread safety", "review for real-time correctness",
  "check RAII", "find latency bottlenecks", "review concurrency", or similar.
  ALSO TRIGGER via /cpp-realtime-reviewer slash command.
  ALSO TRIGGER when the user pastes or attaches .cpp / .hpp / .h files and
  asks for a review, audit, or safety check.
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# C++ Real-Time Reviewer Skill

Perform a structured, severity-tagged code review of C++ source targeted at
**real-time embedded, cryptographic, and secure-networked systems** (QKD, QRNG,
satellite-ground links). Focus on correctness and safety defects that are
dangerous in production — not style nits.

---

## Step 1 — Resolve Scope

Determine what to review from, in order of precedence:

1. **Inline path argument** — `/cpp-realtime-reviewer <path>` uses that path.
2. **Attached / mentioned files** — review only those files.
3. **Pasted code block** — review the code block in the user message.
4. **Working directory** — glob for `**/*.cpp`, `**/*.hpp`, `**/*.h`,
   excluding `build/`, `third_party/`, `vendor/`, `_deps/`, `.git/`.

Announce the resolved scope before continuing:
> "Reviewing scope: `<resolved path, filename, or 'pasted snippet'>`"

---

## Step 2 — Load the Review Checklist

Read the full checklist from:

```
<skill_base_path>/references/review-checklist.md
```

Keep it in context for the entire review. It defines exactly what defect
classes to look for across the five review domains.

---

## Step 3 — Load the Severity Guide

Read the severity classification rules from:

```
<skill_base_path>/references/severity-guide.md
```

Apply these rules consistently when tagging every finding.

---

## Step 4 — Analyse the Code

For each file or snippet in scope, work through all five review domains
defined in the checklist:

| Domain | Focus |
|--------|-------|
| **D1 — Thread Safety & Race Conditions** | Data races, TOCTOU, missing synchronisation, lock ordering |
| **D2 — Synchronisation Primitives** | Mutex misuse, spurious wake-ups, condition variable protocol, atomic ordering |
| **D3 — RAII & Resource Ownership** | Raw `new`/`delete`, unowned handles, exception-safety, smart pointer misuse |
| **D4 — Latency & Hot-Path Hygiene** | Blocking calls in real-time paths, dynamic allocation, lock contention, I/O in ISRs |
| **D5 — Concurrency-Safe Logging** | Unsynchronised format strings, blocking log calls, PII/secret leakage in logs |

For every finding record:
- **Severity** (CRITICAL / WARNING / SUGGESTION) — per the severity guide.
- **Domain** tag (D1–D5).
- **File + line range** of the affected code.
- **What is wrong** — a precise, actionable description.
- **Why it matters** — consequence in a real-time / cryptographic context.
- **Fix** — the correct approach, with a concrete code snippet where possible.

Do not skip domains. Write `No issues found in this domain.` if a domain is
clean.

---

## Step 5 — Load the Report Template

Read the output template from:

```
<skill_base_path>/templates/review-report.md
```

Replace `{{ISO_DATE}}` with today's date, `{{SCOPE}}` with the scope from
Step 1, and `{{FILE_LIST}}` with the comma-separated list of files reviewed.

Fill every section of the template with findings from Step 4.

---

## Step 6 — Populate the Scorecard

At the end of the report, fill the summary scorecard:

| Domain | Issues | Highest severity |
|--------|--------|-----------------|
| D1 Thread Safety | N | CRITICAL / WARNING / SUGGESTION / — |
| D2 Synchronisation | N | … |
| D3 RAII / Ownership | N | … |
| D4 Latency / Hot Path | N | … |
| D5 Logging Safety | N | … |
| **TOTAL** | **N** | |

Also emit an **Overall Risk Rating**:

| Rating | Criteria |
|--------|----------|
| 🔴 HIGH | Any CRITICAL finding present |
| 🟡 MEDIUM | No CRITICAL, but ≥ 1 WARNING |
| 🟢 LOW | Suggestions only |
| ✅ PASS | No findings |

---

## Step 7 — Output the Report

Print the completed report directly in the conversation. Do **not** write a
file to the project unless the user explicitly asks for it.

End with the checklist template section from `templates/review-report.md`
so the user can copy it into a PR or code-review tool.

---

## Skill Rules

- **Real issues only.** Do not flag style nits as CRITICAL. Reserve CRITICAL
  for defects that can cause data corruption, undefined behaviour, deadlock,
  or cryptographic key exposure.
- **Show the bad code.** Always quote the specific lines that contain the
  defect. Never describe a problem without citing the source location.
- **Show the fix.** Every CRITICAL and WARNING finding must include a concrete
  corrected code snippet.
- **Cryptographic sensitivity.** Treat any finding that could expose key
  material, QRNG seeds, or authentication tokens as automatically CRITICAL
  regardless of other heuristics.
- **Real-time sensitivity.** Treat any blocking call (syscall, dynamic alloc,
  mutex lock) in a path annotated as interrupt-driven, time-critical, or
  `noexcept` in a hard-RT context as at least WARNING.
- **Never modify source files.** This skill is read-only. Output goes to the
  conversation only (unless the user asks for a file).
- **Cite line numbers.** Use `file.cpp:42` format throughout. If reviewing a
  pasted snippet with no filename, use `snippet:42`.
