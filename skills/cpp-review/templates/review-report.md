# C++ Real-Time Code Review

<!--
WRITING RULES FOR THE AGENT FILLING THIS TEMPLATE
──────────────────────────────────────────────────
1. Cite exact lines.
   Every finding must include file:line_start–line_end. For pasted snippets
   use snippet:N. Never describe a problem without citing the source location.

2. Show the defective code.
   Quote the relevant lines verbatim in a fenced code block immediately after
   the finding header.

3. Show the fix.
   Every CRITICAL and WARNING must include a corrected code snippet.
   SUGGESTION may include one if it aids clarity.

4. Severity consistency.
   Apply severity-guide.md strictly. Do not inflate or deflate severity to
   soften feedback.

5. Domain tags.
   Every finding header must include the domain tag [D1]–[D5] or [C1]–[C4]
   for QKD/crypto-specific checks.

6. No invented findings.
   Only report defects that are present in the code. Do not fabricate issues.
-->

**Date**: {{ISO_DATE}}
**Scope**: {{SCOPE}}
**Files reviewed**: {{FILE_LIST}}

---

## Findings

<!--
For each finding, use this block:

### [SEVERITY] [DOMAIN] — <Short title>

**File**: `path/to/file.cpp:LINE_START–LINE_END`

```cpp
// Defective code — quoted verbatim
```

**Problem**: <Precise description of the defect and why it is dangerous in a
real-time / cryptographic context.>

**Fix**:

```cpp
// Corrected code
```

---
-->

<!-- Agent: insert findings here, one block per issue, ordered by severity
     (CRITICAL first, then WARNING, then SUGGESTION). -->

---

## No issues found

<!-- Agent: if a domain has no findings, include a one-liner here, e.g.:
     "D3 RAII / Ownership — No issues found."
     This confirms the domain was checked, not skipped. -->

---

## Summary Scorecard

| Domain | Issues | Highest severity |
|--------|--------|-----------------|
| D1 Thread Safety & Race Conditions | | |
| D2 Synchronisation Primitives | | |
| D3 RAII & Resource Ownership | | |
| D4 Latency & Hot-Path Hygiene | | |
| D5 Concurrency-Safe Logging | | |
| QKD / Crypto-Specific (C1–C4) | | |
| **TOTAL** | | |

**Overall Risk Rating**: <!-- 🔴 HIGH / 🟡 MEDIUM / 🟢 LOW / ✅ PASS -->

| Rating | Criteria |
|--------|----------|
| 🔴 HIGH | Any CRITICAL finding present |
| 🟡 MEDIUM | No CRITICAL, but ≥ 1 WARNING |
| 🟢 LOW | Suggestions only |
| ✅ PASS | No findings |

---

## PR / Code-Review Checklist

Copy this into your PR description or code-review tool and tick off each item.

```
## C++ Real-Time Safety Checklist

### D1 — Thread Safety & Race Conditions
- [ ] All shared state accessed under the correct lock or via std::atomic
- [ ] No TOCTOU patterns (check-then-act on shared state without a lock)
- [ ] Multi-mutex acquisitions use std::scoped_lock or std::lock to prevent deadlock
- [ ] Lock ordering is consistent across all call paths
- [ ] No iterators / pointers cached across unlocked windows

### D2 — Synchronisation Primitives
- [ ] All mutex locks managed via RAII (lock_guard / unique_lock / scoped_lock)
- [ ] Condition variable waits use predicate loop or predicate-overload wait()
- [ ] notify_one / notify_all called after (not before) updating the predicate
- [ ] Atomic memory orders are correct (acquire/release paired, not relaxed where ordering matters)
- [ ] No manual .lock() / .unlock() calls

### D3 — RAII & Resource Ownership
- [ ] No raw new / delete outside low-level allocation classes
- [ ] File descriptors, sockets, and OS handles wrapped in RAII types
- [ ] Crypto contexts (EVP_*, SSL_CTX) freed on all code paths via RAII
- [ ] No shared_ptr cycles; weak_ptr used where back-references are needed
- [ ] Cryptographic key buffers zeroed before deallocation (memset_s / OPENSSL_cleanse)

### D4 — Latency & Hot-Path Hygiene
- [ ] No dynamic allocation (new, push_back with realloc) in real-time paths
- [ ] No blocking syscalls (sleep, blocking recv, fflush) in packet/frame handlers
- [ ] Mutex critical sections are minimal (no I/O or long computation inside a lock)
- [ ] Per-thread hot data padded to hardware_destructive_interference_size
- [ ] Pre-allocated / pre-reserved containers used in hot loops

### D5 — Concurrency-Safe Logging
- [ ] Logging library is thread-safe (or calls are serialised)
- [ ] No synchronous flushing log calls (std::endl, fflush) in real-time loops
- [ ] Log calls are outside mutex critical sections
- [ ] No key material, QRNG seeds, or authentication tokens in log messages
- [ ] Format strings are string literals (not user-controlled)

### QKD / Crypto-Specific
- [ ] Key material zeroed immediately after use
- [ ] QRNG seed / entropy source access is synchronised
- [ ] QKD state machine transitions are atomic w.r.t. concurrent observers
- [ ] Secret-dependent comparisons use constant-time primitives
- [ ] No timing side-channels on secret-dependent branches

### Sign-off
- [ ] All CRITICAL findings resolved or have a tracked remediation ticket
- [ ] All WARNING findings resolved or accepted with written justification
- [ ] Reviewer confirms the above checklist was worked through
```

---

*Generated by the `cpp-realtime-reviewer` skill.
Re-run `/cpp-realtime-reviewer <path>` after significant concurrency or
real-time changes.*
