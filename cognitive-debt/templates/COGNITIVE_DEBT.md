# Cognitive Debt Report

<!--
WRITING RULES FOR THE AGENT FILLING THIS TEMPLATE
──────────────────────────────────────────────────
1. Evidence first.
   Every finding must cite file:line and quote the problematic code in a
   fenced block. Never describe a problem without showing the code.

2. Explain the cognitive cost — not the principle.
   Write "A reader must trace three layers to discover this returns null"
   — not "this violates the Law of Demeter". The cognitive cost is what
   matters; the principle is optional background.

3. Concrete recommendations.
   Every HIGH and MEDIUM finding must include a specific, actionable
   recommendation (e.g. "Extract the state enum to …" or "Replace with
   a direct function call at …"). LOW findings may include one if useful.

4. Flag uncertainty.
   Use [UNCERTAIN] inline when a finding might be intentional. Lower
   severity by one level and explain your uncertainty.

5. Severity honesty.
   Apply severity rules from SKILL.md strictly. Do not inflate to emphasise
   a point or deflate to soften feedback.

6. Order findings.
   Within each category section: 🔴 HIGH → 🟡 MEDIUM → 🟢 LOW.

7. "What's Working Well" is mandatory.
   If you find nothing positive to note, recalibrate your findings.
-->

**Date**: {{ISO_DATE}}
**Scope**: {{SCOPE}}
**LOC analysed**: {{LOC}}
**Analysis mode**: {{MODE}}
**Language(s)**: {{LANGUAGES}}

---

## Severity Summary

| Category | 🔴 HIGH | 🟡 MEDIUM | 🟢 LOW | Total |
|----------|---------|----------|-------|-------|
| D1 Dead Code | | | | |
| D2 Over-Engineering | | | | |
| D3 Duplication | | | | |
| D4 Abstraction Quality | | | | |
| D5 Control Flow | | | | |
| D6 Naming | | | | |
| D7 Test Debt | | | | |
| **TOTAL** | | | | |

**Overall Cognitive Load Rating**:
<!-- 🔴 HIGH DEBT / 🟡 MODERATE DEBT / 🟢 LOW DEBT / ✅ MINIMAL DEBT -->

| Rating | Criteria |
|--------|----------|
| 🔴 HIGH DEBT | ≥ 3 HIGH findings, or ≥ 1 HIGH in ≥ 3 categories |
| 🟡 MODERATE DEBT | 1–2 HIGH findings, or ≥ 5 MEDIUM findings |
| 🟢 LOW DEBT | No HIGH findings, ≤ 4 MEDIUM findings |
| ✅ MINIMAL DEBT | No HIGH or MEDIUM findings |

---

## D1 — Dead Code

<!--
For each finding, use this block:

### [SEVERITY] [D1] — <Short title>

**Location**: `path/to/file.py:LINE`
**Confidence**: CERTAIN | LIKELY | UNCERTAIN

```python
# Problematic code — quoted verbatim
```

**Cognitive cost**: <How this slows a reader — be specific, not abstract.>

**Recommendation**: <Concrete action. E.g. "Delete lines 42–67; confirmed
no call sites via grep for `function_name`." or "Replace the `if False:`
block with a comment if the intent must be preserved.">

---
-->

<!-- Agent: insert D1 findings here, ordered 🔴 → 🟡 → 🟢. -->
<!-- If no findings: write "No dead code identified." -->

---

## D2 — Over-Engineering

<!--
For each finding, use this block:

### [SEVERITY] [D2] — <Short title>

**Location**: `path/to/file.ts:LINE`
**Confidence**: CERTAIN | LIKELY | UNCERTAIN

```typescript
// Problematic code — quoted verbatim
```

**Cognitive cost**: <What a reader must learn that adds no value.>

**Recommendation**: <How to simplify.>

---
-->

<!-- Agent: insert D2 findings here. -->
<!-- If no findings: write "No over-engineering identified." -->

---

## D3 — Duplication

<!--
For each finding, use this block:

### [SEVERITY] [D3] — <Short title>

**Locations**:
- `path/to/file_a.go:LINE`
- `path/to/file_b.go:LINE`
**Confidence**: CERTAIN | LIKELY | UNCERTAIN

```go
// First instance — quoted verbatim
```

```go
// Second instance — quoted verbatim (highlight what differs)
```

**Cognitive cost**: <Why having two copies creates friction.>

**Recommendation**: <Where to consolidate and how.>

---
-->

<!-- Agent: insert D3 findings here. -->
<!-- If no findings: write "No significant duplication identified." -->

---

## D4 — Abstraction Quality

<!--
For each finding, use this block:

### [SEVERITY] [D4] — <Short title>

**Location**: `path/to/file.rs:LINE`
**Confidence**: CERTAIN | LIKELY | UNCERTAIN

```rust
// Problematic code — quoted verbatim
```

**Cognitive cost**: <What the abstraction forces readers to know or do.>

**Recommendation**: <How to improve the abstraction boundary, rename it,
or remove it.>

---
-->

<!-- Agent: insert D4 findings here. -->
<!-- If no findings: write "No abstraction quality issues identified." -->

---

## D5 — Control Flow Complexity

<!--
For each finding, use this block:

### [SEVERITY] [D5] — <Short title>

**Location**: `path/to/file.cpp:LINE`
**Confidence**: CERTAIN | LIKELY | UNCERTAIN

```cpp
// Problematic code — quoted verbatim
```

**Cognitive cost**: <How many states or paths a reader must simulate.>

**Recommendation**: <Specific refactoring: early return, extracted helper,
formal state enum, etc.>

---
-->

<!-- Agent: insert D5 findings here. -->
<!-- If no findings: write "No significant control flow complexity identified." -->

---

## D6 — Naming

<!--
For each finding, use this block:

### [SEVERITY] [D6] — <Short title>

**Location**: `path/to/file.ts:LINE`
**Confidence**: CERTAIN | LIKELY | UNCERTAIN

```typescript
// Problematic name in context — quoted verbatim
```

**Cognitive cost**: <The translation burden the reader carries.>

**Recommendation**: <Specific rename or rename strategy.>

---
-->

<!-- Agent: insert D6 findings here. -->
<!-- If no findings: write "No significant naming issues identified." -->

---

## D7 — Test Debt

<!--
For each finding, use this block:

### [SEVERITY] [D7] — <Short title>

**Location**: `path/to/test_file.py:LINE`
**Confidence**: CERTAIN | LIKELY | UNCERTAIN

```python
# Problematic test code — quoted verbatim
```

**Cognitive cost**: <Why this reduces confidence in the test suite.>

**Recommendation**: <How to improve the test.>

---
-->

<!-- Agent: insert D7 findings here. -->
<!-- If no findings: write "No test debt identified." -->

---

## Prioritized Action List

<!--
List the top findings that would deliver the highest reduction in cognitive
load if addressed. Order by: (1) severity, (2) breadth of impact (how many
files or readers are affected), (3) effort required (lower effort first
when severity and breadth are equal).

Format:
1. 🔴 **[D1] Remove `process_legacy_v1()` in `src/pipeline.py`** — unreachable
   since the v2 migration in 2022; ~120 lines that mislead readers about the
   pipeline's capabilities. Delete `src/pipeline.py:45–167`.

2. …
-->

1. <!-- Agent: fill in -->
2. <!-- Agent: fill in -->
3. <!-- Agent: fill in -->
4. <!-- Agent: fill in -->
5. <!-- Agent: fill in -->

<!-- Include up to 10 items. Stop when the remaining items are all 🟢 LOW
     unless the codebase is small enough for exhaustive coverage. -->

---

## What's Working Well

<!--
Note concrete examples of low-cognitive-load patterns found in the codebase.
Be specific — cite files and line ranges where appropriate.

Examples of what to include:
- Consistent use of named constants instead of magic literals across X files
- Clear, predicate-form boolean naming throughout the auth module
- Well-bounded service interfaces that hide implementation details
- Test suite that tests behaviour not implementation in Y module
- Appropriate complexity level — no over-abstraction in the core domain logic

This section is mandatory. At least 3 items are expected. If fewer than 3
positive patterns are visible, recalibrate the findings above.
-->

- <!-- Agent: fill in -->
- <!-- Agent: fill in -->
- <!-- Agent: fill in -->

---

## Analysis Notes

<!--
Use this section for:
- Caveats about analysis coverage (e.g. "the `vendor/` directory was excluded")
- Areas that could not be fully assessed due to codebase size or structure
- Patterns that were borderline and excluded per judgment-guidelines.md
- Suggestions for follow-up analysis (e.g. "dynamic dispatch makes dead code
  harder to detect in this codebase; a runtime tracer would provide more
  certainty")

Omit this section if there are no relevant caveats.
-->

---

*Generated by the `cognitive-debt` skill.
Re-run `/cognitive-debt [path]` after significant refactoring or architectural
changes. Complement this report with `/analyze-codebase` for structure and
dependency analysis and `/code-quality-reviewer` for correctness and security.*
