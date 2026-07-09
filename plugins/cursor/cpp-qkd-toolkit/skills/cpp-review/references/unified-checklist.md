# Unified C++ Review Checklist

Merged from realtime reviewer, production engineer review mode, and QKD
security engineer. Apply lenses to filter domains.

## Lens: --realtime (default for hot paths)

| Domain | Focus |
|--------|-------|
| D1 Thread Safety | Data races, TOCTOU, missing sync, lock ordering |
| D2 Sync Primitives | Mutex misuse, condvar protocol, atomic ordering |
| D3 RAII | Raw new/delete, exception safety, smart pointer misuse |
| D4 Latency | Blocking in hot paths, heap alloc in loops, lock contention |
| D5 Safe Logging | Unsync'd format strings, secrets in logs |

See `references/review-checklist.md` (realtime) and `references/severity-guide.md`.

## Lens: --security (QKD/crypto)

| Domain | Focus |
|--------|-------|
| S1 Auth | Unauthenticated messages, missing replay protection |
| S2 Key Hygiene | Key material in logs, missing zeroization, heap copies |
| S3 Crypto | Custom primitives, nonce/IV reuse, weak algorithms |
| S4 Protocol | QBER threshold handling, key lifetime, atomic consumption |
| S5 Standards | ETSI GS QKD 004/014 conformance |

See `references/etsi-standards.md` and `qkd-examples/` for reference reviews.

**Always state threat model first:** assets, trust boundaries, adversary capabilities.

## Lens: --full

Apply all D1–D5 and S1–S5 domains. Deduplicate findings across lenses.

## Shared Invariants (all lenses)

- Key material NEVER in logs — CRITICAL in every lens
- Mutex protects specific state — cite which
- C++17 compatible patterns only

## Severity (unified)

| Level | When |
|-------|------|
| CRITICAL | Security vuln, data race, key leak, production crash |
| WARNING | Significant reliability/maintainability defect |
| SUGGESTION | Style, minor improvement |

## Output

Use `templates/review-report.md`. Include scorecard and PR checklist.

For large reviews, spawn `cpp-security-reviewer` or `cpp-realtime-reviewer`
subagents in parallel via Task tool.
