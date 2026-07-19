# Agent STE — Validation Checklist

Another agent must be able to answer every item **YES** or **NO** from the
instruction text alone. Mark **N/A** only where the item explicitly allows it.

## How to use

1. Target = the candidate Agent STE instruction block.
2. Answer each question YES/NO/(N/A).
3. **Required** items must be YES (or allowed N/A) before planning or execution.
4. Any Required NO → revise; do not proceed.

---

## A. Structure (Required)

| # | Question | Answer |
|---|----------|--------|
| A1 | Is there exactly one `OBJECTIVE` sentence with one primary deliverable (no independent goals joined by “and”)? | YES/NO |
| A2 | Is there an `ENTITIES` table or list with stable IDs? | YES/NO |
| A3 | Does every action sentence name an explicit actor ID? | YES/NO |
| A4 | Does every action sentence name an explicit object ID or path? | YES/NO |
| A5 | Are actions numbered with explicit order (or explicit PARALLEL)? | YES/NO |
| A6 | Are `SCOPE.IN` and `SCOPE.OUT` both present? | YES/NO |
| A7 | Is a local `GLOSSARY` present for critical terms (or statement `GLOSSARY: NONE — no overloaded terms`)? | YES/NO |

## B. Determinism / lexicon (Required)

| # | Question | Answer |
|---|----------|--------|
| B1 | Is the text free of: optimize, improve, better, appropriate, reasonable, quickly, carefully, if necessary, as needed, etc., and so on, normally, probably, maybe, somehow? | YES/NO |
| B2 | Is the text free of subjective gates: satisfied, looks good, obvious, tidy, harden (unqualified)? | YES/NO |
| B3 | When ≥2 entities appear, are pronouns `it/they/this/that` absent for those entities? | YES/NO |
| B4 | Does each critical term use only one meaning consistent with the glossary? | YES/NO |
| B5 | Is each sentence limited to one action (no “do X and Y” conjunctions of actions)? | YES/NO |

## C. Inputs / outputs / artifacts (Required)

| # | Question | Answer |
|---|----------|--------|
| C1 | Are inputs listed with source and format (or `INPUTS: NONE`)? | YES/NO |
| C2 | Are outputs/artifacts listed with destination/path and format (or `OUTPUTS: NONE`)? | YES/NO |
| C3 | Are quantities paired with units where quantities appear? | YES/NO / N/A if no quantities |

## D. Success, failure, validation (Required)

| # | Question | Answer |
|---|----------|--------|
| D1 | Is there at least one checkable SUCCESS criterion (command, metric, exit code, or countable property)? | YES/NO |
| D2 | Is there at least one FAILURE condition with a named next action? | YES/NO |
| D3 | Is there a VALIDATION PROCEDURE with expected results? | YES/NO |
| D4 | Is there a COMPLETION CHECKLIST with ≥2 concrete items? | YES/NO |

## E. Agent hazard slots (Required for mutating work)

Answer N/A **only if** the instruction is explicitly read-only and states `SIDE EFFECTS: NONE`.

| # | Question | Answer |
|---|----------|--------|
| E1 | Are PRECONDITIONS listed? | YES/NO/N/A |
| E2 | Are POSTCONDITIONS listed? | YES/NO/N/A |
| E3 | Are INVARIANTS listed (or `INVARIANTS: NONE`)? | YES/NO/N/A |
| E4 | Is ROLLBACK specified (steps or `NONE — <reason>`)? | YES/NO/N/A |
| E5 | Is IDEMPOTENCY stated (`SAFE TO RE-RUN: yes/no` + behavior)? | YES/NO/N/A |
| E6 | Are SIDE EFFECTS listed (or `NONE`)? | YES/NO/N/A |
| E7 | Are PERMISSIONS REQUIRED listed (or `NONE`)? | YES/NO/N/A |
| E8 | Are EXTERNAL DEPENDENCIES listed (or `NONE`)? | YES/NO/N/A |

## F. Honesty about unknowns (Required)

| # | Question | Answer |
|---|----------|--------|
| F1 | If a required metric/threshold/path is missing, is it marked `UNKNOWN` with halt/ask (not fabricated)? | YES/NO/N/A |
| F2 | Are ASSUMPTIONS written with an IF FALSE branch? | YES/NO |

## Pass rule

**PASS** iff:

- All Required answers in A–D and F are YES or allowed N/A
- All Required answers in E are YES or allowed N/A under the read-only exception

**FAIL** otherwise. Return the list of failing item IDs to the authoring agent.
