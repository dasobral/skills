# Code Quality Review

<!--
WRITING RULES FOR THE AGENT FILLING THIS TEMPLATE
──────────────────────────────────────────────────
1. Cite exact lines.
   Every finding must include file:line or snippet:line. Never describe a
   problem without citing the source location.

2. Show the defective code.
   Quote the relevant lines verbatim in a fenced code block immediately
   after the finding header. Use the correct language identifier for
   syntax highlighting (python, typescript, java, go, etc.).

3. Show the fix.
   Every CRITICAL and WARNING must include a corrected code snippet.
   SUGGESTION may include one if it aids clarity.

4. Severity consistency.
   Apply the severity rules from SKILL.md strictly. Do not inflate or
   deflate severity to soften feedback.

5. Pillar tags.
   Every finding header must include the pillar tag [P1]–[P4].

6. No invented findings.
   Only report defects present in the code. Do not fabricate issues.

7. Order findings.
   Within each pillar section: CRITICAL → WARNING → SUGGESTION.
-->

**Date**: {{ISO_DATE}}
**Scope**: {{SCOPE}}
**Files reviewed**: {{FILE_LIST}}

---

## P1 — Clarity

<!--
For each finding, use this block:

### [SEVERITY] [P1] — <Short title>

**Location**: `path/to/file.py:LINE`

```python
# Problematic code — quoted verbatim
```

**Problem**: <Precise description of the issue and why it hurts readability
or comprehension.>

**Fix**:

```python
# Corrected code
```

---
-->

<!-- Agent: insert P1 findings here, ordered CRITICAL → WARNING → SUGGESTION. -->
<!-- If no issues: write "No issues found in this pillar." -->

---

## P2 — Simplicity

<!-- Agent: insert P2 findings here. -->
<!-- If no issues: write "No issues found in this pillar." -->

---

## P3 — Good Practices

<!-- Agent: insert P3 findings here. -->
<!-- If no issues: write "No issues found in this pillar." -->

---

## P4 — Security

<!-- Agent: insert P4 findings here. -->
<!-- If no issues: write "No issues found in this pillar." -->

---

## Health Summary

| Pillar | Issues | Highest severity |
|--------|--------|-----------------|
| P1 Clarity | | |
| P2 Simplicity | | |
| P3 Good Practices | | |
| P4 Security | | |
| **TOTAL** | | |

**Overall Health Rating**: <!-- 🔴 CRITICAL / 🟡 NEEDS WORK / 🟢 HEALTHY / ✅ EXCELLENT -->

| Rating | Criteria |
|--------|----------|
| 🔴 CRITICAL | Any CRITICAL finding present |
| 🟡 NEEDS WORK | No CRITICAL, but ≥ 1 WARNING |
| 🟢 HEALTHY | Suggestions only |
| ✅ EXCELLENT | No findings |

---

## PR / Code-Review Checklist

Copy this into your PR description or code-review tool and tick off each item.

```
## Code Quality Checklist

### P1 — Clarity
- [ ] All names clearly communicate intent without requiring implementation trace
- [ ] No unexplained abbreviations or single-letter names outside conventional scopes
- [ ] No magic numbers or magic strings; named constants used throughout
- [ ] Functions are short (≤ ~40 lines) and do one thing
- [ ] Nesting depth is ≤ 3 levels; early returns used to flatten logic
- [ ] No commented-out dead code or unreachable code blocks
- [ ] Comments explain WHY, not WHAT; no stale or misleading comments
- [ ] Public APIs are documented (params, return value, error conditions)

### P2 — Simplicity
- [ ] No custom reimplementation of standard library functionality
- [ ] No abstractions, generics, or patterns added without a current use case
- [ ] No feature flags, plugin systems, or DI containers where not needed
- [ ] No speculative or unused code, exports, or configuration paths
- [ ] Duplicated logic (≥ 3 copies) extracted into a shared function or constant

### P3 — Good Practices
- [ ] Each class / module has a single, clear responsibility (SRP)
- [ ] New types extend via composition or new classes, not by modifying existing code (OCP)
- [ ] Subclasses honour their parent's contract (LSP)
- [ ] Interfaces / protocols are narrow and focused (ISP)
- [ ] Business logic depends on abstractions, not concrete implementations (DIP)
- [ ] Errors are propagated to callers; none silently swallowed
- [ ] Error messages are actionable and include context
- [ ] External dependencies (I/O, clock, network) are injected for testability
- [ ] No circular imports or circular dependencies between modules

### P4 — Security
- [ ] No user input interpolated directly into SQL, shell commands, or templates
- [ ] Parameterised queries / prepared statements used for all DB access
- [ ] All external input validated for type, length, range, and format
- [ ] No hardcoded passwords, API keys, tokens, or connection strings
- [ ] No unsafe deserialization (pickle on untrusted data, yaml.load, XXE)
- [ ] Authorization checks applied on every endpoint / handler
- [ ] Passwords stored with bcrypt / Argon2 / scrypt (never MD5/SHA-1/plain)
- [ ] Dependencies pinned to exact versions via a lockfile
- [ ] No known-vulnerable dependencies (outdated, CVEs)
- [ ] Sensitive data encrypted at rest and in transit; not leaked in logs or errors
- [ ] Cryptographically secure RNG used where randomness must be unpredictable

### Sign-off
- [ ] All CRITICAL findings resolved or have a tracked remediation ticket
- [ ] All WARNING findings resolved or accepted with written justification
- [ ] Reviewer confirms the above checklist was worked through
```

---

*Generated by the `code-quality-reviewer` skill.
Re-run `/code-quality-reviewer <path>` after significant refactoring or
security-relevant changes.*
