# Shared Review Heuristics

Cross-reference for `review-quality` and `audit-cognitive-debt` to avoid
duplicate findings with conflicting severity scales.

## Severity Mapping

| review-quality | audit-cognitive-debt | Meaning |
|----------------|---------------------|---------|
| CRITICAL | HIGH | Security risk or severe maintenance burden |
| WARNING | MEDIUM | Measurable friction or technical debt |
| SUGGESTION | LOW | Minor improvement, debatable trade-off |

## Overlap Zones — Single Source of Truth

| Topic | Primary skill | Secondary defers to |
|-------|--------------|---------------------|
| Over-engineering, premature abstraction | review-quality P2 | audit D2 references P2 |
| Naming clarity | review-quality P1 | audit D6 references P1 |
| Test quality (over-mocking, trivial tests) | review-quality P3 | audit D7 references P3 |
| Security (injection, secrets, deserialization) | review-quality P4 | audit does not duplicate |
| Dead code, duplication, control flow | audit-cognitive-debt D1/D3/D5 | review-quality does not duplicate |
| Abstraction quality (leaky, god objects) | audit-cognitive-debt D4 | review-quality P2 for over-abstraction only |

When both skills run on the same scope, deduplicate in conversation output.
Prefer the primary skill's severity scale.

## Modern Model Context

Reviews target code maintained by AI-assisted workflows (Cursor Agent, cloud
agents, subagents). Flag patterns that confuse agents:
- Implicit conventions not captured in CODING_REQUIREMENTS.md
- Mixed paradigms in the same module
- Undocumented side effects or global state
