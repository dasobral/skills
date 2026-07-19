# Changelog

## 2.4.0 — 2026-07-19

### Added

- **`agent-ste`** skill in the `agent-platform` plugin — Agent Simplified
  Technical English: controlled instruction language for LLM execution
  (purpose, philosophy, transformation algorithm, mandatory rules, forbidden
  patterns, eight worked examples, validation checklist, and draft Spec v1.0).
- Design note: `docs/superpowers/specs/2026-07-19-agent-ste-design.md`.

### Changed

- `agent-platform` Cursor and Codex adapter READMEs document `agent-ste` in the
  daily workflow.
- Landing registry assignments may include non-workflow portable skills
  alongside the five evidence workflow plugins.

## 2.3.0 — 2026-07-09

### Added

- **`plugins/codex/`** — eleven generated, committed native Codex plugins and
  `.agents/plugins/marketplace.json`.
- Codex adapters, safe local Python agent-template installation, and native
  manifest/skill/hook/agent validation.
- Isolated Codex CLI coverage for the officially documented local marketplace
  `add` and `list` commands. Local plugin installation remains a ChatGPT
  desktop app workflow; the tests do not claim CLI plugin loading.
- Five Codex workflow plugins:
  - `agentic-trust-gate`
  - `agent-attack-replay`
  - `crypto-change-radar`
  - `entropy-flight-recorder`
  - `scientific-claim-ledger`
- Evidence contracts and scenarios for trust/MCP drift, agent attack replay,
  cryptographic and PQC change, entropy qualification, and scientific claims.

### Changed

- `skills-maintain` now validates core, regenerates six Cursor and eleven Codex
  native plugins, validates both generated trees, and then exports flat skills.
- `skills-export sync codex` owns native Codex generation; `export codex`
  remains the separate flat export at `dist/codex/skills/`.
- `skills-install codex --plugins --project|--user` installs native plugin and
  marketplace files without automatically installing custom agents.
- Codex hooks require explicit trust review. Static validation proves shape and
  path containment, not that hook behavior is trustworthy.

### Security and evidence

- Workflow outputs preserve `unknown`, `not-applicable`, and `evidence-gap`
  states instead of fabricating certainty when evidence or optional tools are
  unavailable.
- Workflow plugins do not certify agent/repository safety, cryptographic or
  entropy adequacy, standards compliance, scientific validity, or release
  readiness; authorization, sandboxing, secret handling, and expert review
  remain user responsibilities.

## 2.2.0 — 2026-07-09

### Added

- **`scripts/cron/`** — maintainable cron setup:
  - `skills-maintain.sh` wrapper (PATH, PyYAML check, logging, exit codes)
  - `install.sh` / `uninstall.sh` to configure schedule/repo and manage crontab
  - `config.env.example` for basics (schedule, python, log path)
- **`plugins/cursor/`** — Cursor plugins live here (ready-to-use target)
- **`./bin/skills-install cursor --plugins --user`** — install full plugins to `~/.cursor/plugins/local/`

### Changed

- Cursor sync/maintain now writes to **`plugins/cursor/`** instead of repo root
- Marketplace `source` paths updated to `plugins/cursor/<name>`
- Docs clarify Cursor-first layout; Claude/Codex remain `dist/` exports

### Migration

Root plugin folders (`codecraft/`, etc.) moved to `plugins/cursor/`. Re-run:

```bash
./bin/skills-export sync cursor
```

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
