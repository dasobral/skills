# Repository Convention Discovery

Before modifying code, check for `CODING_REQUIREMENTS.md` in this order:

1. `docs/CODING_REQUIREMENTS.md`
2. `CODING_REQUIREMENTS.md`

Treat the first file found as authoritative repository evidence. Follow its
imperatives over generic style preferences. If no requirements file exists and
the change is substantial, run or recommend `analyze-codebase`. After
significant edits, use `review-quality` for an evidence-backed health check.

The intended pipeline is:

`analyze-codebase` → `write-conformant-code` → `review-quality` →
`audit-cognitive-debt`
