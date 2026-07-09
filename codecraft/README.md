# Codecraft

End-to-end code quality for AI-assisted development.

## Skills

| Skill | Purpose |
|-------|---------|
| `analyze-codebase` | Extract conventions → `CODING_REQUIREMENTS.md` |
| `write-conformant-code` | Implement code matching project style |
| `review-quality` | Four-pillar review (clarity, simplicity, practices, security) |
| `audit-cognitive-debt` | Cognitive friction audit → `COGNITIVE_DEBT.md` |

## Pipeline

```
analyze-codebase → write-conformant-code → review-quality → audit-cognitive-debt
```

## Agents

- `code-reviewer` — parallel module reviews
- `convention-analyst` — deep convention extraction

## Hooks

- `sessionStart` — warns when `CODING_REQUIREMENTS.md` is stale (>30 days)

## Install

```bash
# From marketplace repo root
cursor plugin install ./codecraft
```

Or copy to `~/.cursor/plugins/local/codecraft/`.
