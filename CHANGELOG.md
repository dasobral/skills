# Changelog

## 2.0.0 — 2026-07-09

### Breaking

- Restructured from 13 standalone Claude Code skills to 6 Cursor plugins
- Removed flat skill directories at repo root
- Renamed several skills (see README consolidation map)

### Added

- `.cursor-plugin/marketplace.json` for multi-plugin discovery
- Per-plugin manifests, agents, rules, and hooks
- Shared review heuristics (codecraft) and unified C++ review lenses (cpp-qkd-toolkit)
- Hardware-adaptive local inference guide (aos-stack)
- Generalized career profile template (career-writer)

### Merged

- `code-quality-reviewer` + `cognitive-debt` → shared heuristics, distinct outputs
- `cpp-production-engineer` + `cpp-realtime-reviewer` + `qkd-security-engineer` → `cpp-engineer` + `cpp-review`
- `ml-inference-optimizer` + `rust-systems-engineer` → `local-inference` + `rust-systems`
- `agent-creator` + `agent-orchestrator` → `create-agent` + `orchestrate`
