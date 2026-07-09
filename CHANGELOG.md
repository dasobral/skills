# Changelog

## 2.1.0 — 2026-07-09

### Added

- **`landing/`** drop zone for skills from any platform (portable, Claude, Codex, Cursor)
- **`skills-export ingest`** — normalize and merge landing → `core/skills/`
- **`skills-export maintain` / `translate`** — full ingest + validate + export pipeline
- **`bin/skills-maintain`** — one-shot autonomous maintenance
- **`bin/skills-install`** — install `dist/` exports to standard platform paths
- Platform normalization (`normalize.py`) for portable core

### Added (prior 2.1.0 commit on branch)

- **Portable core** (`core/skills/`, `core/manifest.yaml`) as single source of truth
- **skills-export** CLI — export/sync to Cursor, Claude Code, and Codex
- **Adapters** (`adapters/cursor/`, `adapters/claude/`, `adapters/codex/`)
- Platform-neutral skill bodies with `platform-paths.md` and `platform-orchestration.md`
- `bin/skills-export` repo-local launcher

### Changed

- Root Cursor plugins are **generated** via `skills-export sync cursor`
- Edit skills in `core/skills/` only; Cursor extensions in `adapters/cursor/`

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
