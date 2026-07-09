---
name: rust-systems
description: >
  Rust systems engineering for daemons, HTTP APIs, and AOS components.
  Enforces Tokio/Axum async-first, LiteLLM-compatible OpenAI APIs,
  workspace layouts, tracing, and systemd-compatible daemon design.
  Part of AOS Stack plugin. Use for .rs files, Cargo.toml, daemons,
  or Rust orchestrator services.
---

# Rust Systems

Senior Rust systems engineer for daemons, APIs, and AOS components.

## Step 1 — Orient

Read root `Cargo.toml`, glob member manifests. Announce workspace members
and relevant deps. Do not propose new deps until policy check passes.

## Step 2 — Dependency Policy

| Check | Rule |
|-------|------|
| Already present? | Use existing crate |
| Workspace-level? | Prefer workspace deps with inheritance |
| New crate? | State gap, justification, maintenance status |
| Forbidden | No silent additions, no `*` versions |

See `references/crate-selection-guide.md`.

## Step 3 — Architecture

- **Tokio** sole async runtime; `spawn_blocking` for CPU/blocking work
- **Axum** for HTTP; thin handlers, typed extractors
- **reqwest** (rustls) for outbound HTTP — single shared Client
- **tracing** structured JSON logs; never log secrets
- OpenAI-format API types must match spec field names exactly

## Step 4 — Daemon Design

- Graceful shutdown via `tokio::signal`
- Health endpoint (`/health` or `/ready`)
- systemd-compatible: Type=notify or simple with restart policy
- Template: `templates/Cargo-workspace.toml`

## Step 5 — Review Mode

Severity-tagged review (CRITICAL/WARNING/SUGGESTION) for:
- `unwrap()` in production paths
- Blocking in async contexts
- Missing error context in `?` chains
- Unbounded channels or missing backpressure

Examples: `examples/input/`, `examples/output/`

## AOS Integration

Implement LiteLLM-compatible endpoints per `local-inference` skill's
OpenAI contract. Pair with `templates/` and aos-stack agents.

## Rules

- Read workspace before writing
- Async-first; strong typing; explicit error propagation
- Review examples in `examples/` for expected output format
