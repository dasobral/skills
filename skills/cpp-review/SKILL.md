---
name: cpp-review
description: >
  Unified C++ review for QKD/defense systems with three lenses: --realtime
  (concurrency, latency, RAII), --security (crypto hygiene, ETSI, threat
  model), --full (both). Replaces separate realtime and security reviewer
  skills. Part of C++ QKD Toolkit plugin.
  Use when reviewing C++ for race conditions, thread safety, QKD security,
  or production correctness.
---

# C++ Review

Structured review of C++ for real-time, cryptographic, and secure-networked
systems (QKD, QRNG, satellite-ground links).

## Step 1 — Resolve Scope & Lens

Scope: path argument → attached files → pasted code → `**/*.{cpp,hpp,h}` glob.

Lens (from user request or default):
- `--realtime` — concurrency, hot-path latency, RAII
- `--security` — QKD/crypto hygiene, ETSI, threat model
- `--full` — all domains

Announce: `Reviewing scope: <path> | Lens: <lens>`

## Step 2 — Load Checklist

Read `references/unified-checklist.md` and lens-specific references:
- Realtime: `references/review-checklist.md`, `references/severity-guide.md`
- Security: `references/etsi-standards.md`

## Step 3 — Threat Model (security/full lenses)

Before findings, state:
1. Assets (keys, credentials, auth tokens)
2. Trust boundaries
3. Adversary capabilities

## Step 4 — Analyze

Work through applicable domains from unified checklist. Per finding:
severity, domain tag, file:line, bad code quote, fix snippet.

## Step 5 — Report

Use `templates/review-report.md`. Examples in `examples/` and `qkd-examples/`.

For >3 files, parallelize with `cpp-realtime-reviewer` and `cpp-security-reviewer`
subagents, then synthesize.

## Rules

- Read-only unless user asks for fixes
- Key material in logs is always CRITICAL
- Never skip threat model for security lens
