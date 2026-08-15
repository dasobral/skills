# Skills ecosystem SOTA and repo update design

**Status:** Approach B implemented in 2.6.0. This document is the analysis that led to that change.

**Date:** 2026-08-14

**Question:** Is this repository redundant with Vercel’s `npx skills` CLI, or does it still solve a real problem? If it still does, what is the smallest update that uses existing tools instead of competing with them?

## Verdict

This repository is **not wasting time as a skill library and plugin family author**. It **is** wasting time as a **cross-agent skills installer**.

Vercel’s CLI is now the de facto package manager for Agent Skills (`SKILL.md`) across 70+ harnesses. Agent Plugins 1.0.0 (2026-08-06) is the de facto portable **plugin** format for skills + MCP. This repo’s original job — “translate plugins so they are reusable across agents” — has been split by the industry:

| Layer | What it is | Who owns it now |
| --- | --- | --- |
| Skill format | `SKILL.md` + scripts/references | [Agent Skills spec](https://agentskills.io/specification) |
| Skill install / update / discovery | `npx skills add owner/repo` | [Vercel skills CLI](https://github.com/vercel-labs/skills) + [skills.sh](https://skills.sh) |
| Portable plugin package | root `plugin.json` + `skills/` + `mcp.json` | [Agent Plugins 1.0.0](https://agent-plugins.org) |
| Client extras | agents, hooks, rules, commands | Still vendor-specific; explicitly **out of** Agent Plugins v1 |

The remaining unique value here is **content + workflow plugins + client extras**, not another installer. The smartest update is to become a well-formed **authoring and packaging** repo that Vercel CLI, Cursor, Codex, Copilot, and VS Code can consume without a custom install path for skills.

---

## 1. What this repo actually does today

Source of truth (from `README.md` and `docs/superpowers/specs/2026-07-21-simplify-architecture-design.md`):

- `core/skills/` — 26 portable Agent Skills
- `core/manifest.yaml` — 11 named plugin families mapping skills → plugins
- `adapters/{cursor,claude,codex}/` — platform scaffolding (agents, hooks, rules)
- `landing/` — ingest drop zone
- `tools/skills-export/` — assemble `core` + adapters into `dist/`
- `bin/skills-install` — copy assembled trees into user/project paths

Two install modes exist:

1. **Flat skills** — copy `SKILL.md` trees into `~/.cursor/skills`, `~/.claude/skills`, `.agents/skills`, etc.
2. **Native plugins** — assemble vendor plugin trees (`.cursor-plugin`, `.claude-plugin`, `.codex-plugin`) plus marketplaces.

Cursor and Codex adapters are rich (agents, hooks, rules, evidence scripts). The Claude adapter directory contains only a README; Claude “plugins” generated today are skills-only wrappers.

The July 21 simplification already stopped committing generated plugin copies. That was correct. It did not stop this repo from **reimplementing skill installation**.

---

## 2. SOTA as of 2026-08-14

### 2.1 Agent Skills (format)

Anthropic published Agent Skills as an open standard (2025-12-18). A skill is a directory with `SKILL.md`: YAML frontmatter (`name`, `description` required) plus markdown instructions, optional `scripts/`, `references/`, `assets/`. Progressive disclosure is the loading model.

This repo already authors to that format. Frontmatter `name`/`description`/`license` match the spec. Descriptions sampled here are under the 1024-character cap. That layer is aligned.

Community usage: ~40 products on the agentskills.io showcase by mid-2026 (Claude, Codex, Copilot, Cursor, Gemini CLI, Goose, OpenCode, VS Code, and others). A skill written to the spec is the portable unit. **Do not invent a parallel skill format.**

### 2.2 Vercel `npx skills` (distribution)

[vercel-labs/skills](https://github.com/vercel-labs/skills) (~29k stars) is the community installer. `npx add-skill` is deprecated. Current interface:

```bash
npx skills add <owner/repo>
npx skills add <owner/repo> -g -a cursor -a claude-code -a codex
npx skills add <owner/repo> --skill analyze-codebase --list
npx skills find [query]
npx skills update
npx skills list
```

It installs to 70+ agents, supports project vs global scope, symlink vs copy, lock files, and skills.sh discovery. That is exactly the flat-install job of `./bin/skills-install` without `--plugins`, for far more harnesses than the three this repo targets.

Well-known discovery paths include repo-root `skills/`, `.agents/skills/`, `.claude/skills/`, `.cursor/skills/`, and many vendor folders. **`core/skills/` is not a well-known path.** If nothing is found in those folders, the CLI falls back to a recursive search.

It also reads Claude plugin manifests (`.claude-plugin/marketplace.json` / `plugin.json`) and, in current source, skill paths declared in plugin manifests.

It does **not** install Cursor agents, Codex agent TOML, hooks, rules, or native plugin marketplaces. Compatibility table in the CLI README: hooks are Claude/Cline/Kiro-oriented; most agents only get basic skills.

### 2.3 Agent Plugins 1.0.0 (portable plugin packaging)

Published 2026-08-06. TSC includes AWS, Cursor, Microsoft, OpenAI, Vercel.

Canonical package:

```text
my-plugin/
├── plugin.json          # required: $schema + name
├── skills/<name>/SKILL.md
├── mcp.json             # optional
└── com.example.client/  # optional client extension directory
```

v1 standardizes **only skills and MCP servers**. Agents, hooks, commands, and rules stay with clients, via `extensions` in `plugin.json` and/or a reverse-domain directory. That boundary is intentional and matches this repo’s adapter split.

Launch clients: ChatGPT/Codex, Cursor, GitHub Copilot, Kiro, VS Code. Claude Code is **not** in the v1 launch set; it still uses `.claude-plugin/`.

Cursor now documents two formats:

| Format | Manifest | Components |
| --- | --- | --- |
| Agent Plugins | root `plugin.json` | skills, MCP |
| Cursor Plugins | `.cursor-plugin/plugin.json` | skills, MCP, rules, agents, commands, hooks, variables |

Codex CLI 0.146+ maps Agent Plugins `plugin.json` into Codex, and keeps `.codex-plugin/plugin.json` (or `com.openai` extensions) for apps, hooks, and interface. Dual-manifest is the intended migration path, not three generated skill copies.

### 2.4 Vendor plugin marketplaces (still real)

These have not disappeared:

- Cursor: `.cursor-plugin/marketplace.json` + per-plugin `.cursor-plugin/plugin.json`
- Codex: `.agents/plugins/marketplace.json` + `.codex-plugin/plugin.json`
- Claude Code: `.claude-plugin/marketplace.json` + `.claude-plugin/plugin.json`

Community still publishes dual manifests (Claude + Codex) because extras are not portable. Agent Plugins does not replace those extras; it replaces the **skills+MCP packaging** this repo currently emits three times.

### 2.5 What the community is using

Typical author workflow in 2026:

1. Write `SKILL.md` to the Agent Skills spec.
2. Put skills under `skills/` (or inside an Agent Plugin).
3. Users install with `npx skills add owner/repo`.
4. If grouping + MCP matter, add root `plugin.json` (Agent Plugins).
5. If a client needs agents/hooks/rules, add that client’s overlay, not a new skill format.

This repo currently does (1) well, (2) in a non-standard directory, (3) with a custom installer, (4) with vendor manifests instead of Agent Plugins, (5) with a genuine adapter layer that is still needed.

---

## 3. Alignment scorecard

| Concern | This repo | SOTA | Gap |
| --- | --- | --- | --- |
| Skill file format | `SKILL.md` + frontmatter | Agent Skills spec | Aligned |
| Skill location | `core/skills/` | `skills/` or plugin `skills/` | **Misaligned** — Vercel CLI only finds these via recursive fallback |
| Skill install | `./bin/skills-install` (3 agents) | `npx skills add` (70+ agents) | **Redundant** |
| Plugin grouping | `core/manifest.yaml` families | Agent Plugins `plugin.json` + `skills/` | **Parallel, not standard** |
| Portable plugin manifest | `.cursor-plugin` / `.claude-plugin` / `.codex-plugin` generated | root `plugin.json` with Agent Plugins schema | **Behind** |
| MCP packaging | rare `.mcp.json` copies | `mcp.json` per Agent Plugins | Behind / unused |
| Agents / hooks / rules | adapters per platform | client extensions; not in v1 | **Still unique and needed** |
| Evidence workflow plugins | Codex-only families with scripts, schemas, hooks | no standard equivalent | **Still unique** |
| Claude extras | empty adapter | Claude marketplace plugins | No extra value beyond skills |
| Test/example skills | `landing/examples/sample-landing-skill` | `metadata.internal` or outside discovery | **Leaks into Vercel CLI** |

---

## 4. Empirical: Vercel CLI against this repo

Ran `npx skills@latest add /workspace --list` (skills 1.5.22) on 2026-08-14.

Result: **Found 30 skills** via recursive fallback (no well-known `skills/` directory).

Included correctly: all 26 `core/skills/` entries.

Included incorrectly (should not be user-installable from the public repo):

- `sample-landing-skill` — landing template under `landing/examples/`
- `install-plugin-agents` — Codex-only adapter helper
- `check-crypto-runtime` — Codex adapter-only
- `check-entropy-runtime` — Codex adapter-only

Not included: test fixture `fixture-skill` (likely ignored by search depth / ignore rules). That is luck, not a contract.

Conclusion: **`npx skills add dasobral/skills` already works today**, but it is accidental and slightly dirty. It does not install plugins, agents, hooks, or rules.

### How to install skills with Vercel CLI right now

From GitHub (after this repo is public/cloned by the CLI):

```bash
# See what would be installed
npx skills add dasobral/skills --list

# Project-local, detected agents
npx skills add dasobral/skills -y

# Global, specific agents
npx skills add dasobral/skills -g -a cursor -a claude-code -a codex -y

# One plugin family's skills (example: codecraft)
npx skills add dasobral/skills \
  --skill analyze-codebase \
  --skill write-conformant-code \
  --skill review-quality \
  --skill audit-cognitive-debt \
  -y
```

From a local checkout:

```bash
npx skills add /path/to/skills --list
npx skills add /path/to/skills -g -a cursor -y
```

Until discovery hygiene lands, also pass `--skill` names explicitly, or expect the four extra non-portable skills listed above.

Native Cursor/Codex **plugins** (agents, hooks, rules) still require this repo’s assembler:

```bash
./bin/skills-install cursor --plugins --user
./bin/skills-install codex --plugins --project
```

Claude plugin install via this repo is skills-only; prefer the Vercel CLI for Claude.

---

## 5. Unique value vs redundancy

### Keep (real problem)

1. **Domain skill content** that skills.sh does not replace: QKD/C++, crypto CBOM/PQC, entropy qualification, scientific claim ledger, agent attack replay, repository trust / MCP drift, Agent STE.
2. **Plugin families as product units** (Codecraft, C++ QKD Toolkit, …) with a coherent workflow, not a flat dump of 26 skills.
3. **Deterministic evidence scripts, schemas, and contracts** inside those skills. That is closer to “workflow packages” than to prompt snippets.
4. **Client extras** Cursor and Codex still cannot share: Markdown vs TOML agents, `.mdc` rules, hook event contracts. Agent Plugins v1 will not absorb these soon (future considerations list permissions, provenance, secrets — not agents/hooks).
5. **Landing ingest + validation** for authoring (normalize, orphan checks, plugin assignment). That is a maintainer tool, not a user installer.

### Stop competing with

1. Flat skill install into agent directories — Vercel CLI.
2. Supporting 70+ harnesses — Vercel CLI.
3. Skill discovery/search/update/lockfiles — Vercel CLI + skills.sh.
4. Triple-emitting the same `SKILL.md` into Cursor/Claude/Codex plugin trees solely so skills can be found.
5. Claude native plugins, unless Claude-specific agents/commands/hooks are actually authored. Today they are not.

---

## 6. Approaches

### Approach A — Docs-only + discovery hygiene (smallest)

Keep `core/` + adapters + `skills-export` as they are.

Changes:

- Document `npx skills add dasobral/skills` as the supported skill install.
- Mark `sample-landing-skill` and Codex-only helper skills `metadata.internal: true`, or move them off the recursive search path.
- Optionally add `skills/` as a well-known alias (symlinks or a thin export) so discovery is not a fallback.

Do not delete `skills-install` yet.

**Pros:** hours of work; users can install immediately; no architecture fight.  
**Cons:** still three generated plugin formats; still a redundant installer; still not Agent Plugins; still confusing “which command do I run?”.

**Use if:** you only wanted skill install and will drop plugin translation.

### Approach B — Authoring repo; outsource skill install (recommended)

Reposition the repo:

> Portable Agent Skills and Agent Plugins live here. Vercel CLI installs skills. Native marketplaces / client overlays install extras. This repo does not ship a competing skills package manager.

Concrete shape:

```text
skills/                         # well-known Agent Skills tree (source of truth, or generated alias of core)
plugins/<family>/
  plugin.json                   # Agent Plugins 1.0.0
  skills/ → ../../skills/...    # grouped view, no content fork
  com.anysphere.cursor/ or keep .cursor-plugin overlay for extras
  com.openai/ or keep .codex-plugin overlay for extras
adapters/<client>/<family>/     # only extras that are not portable
```

Tooling:

- **Users, skills:** `npx skills add dasobral/skills` (and `--skill` for a family).
- **Users, Cursor extras:** keep a thin `skills-install cursor --plugins` *or* a committed Cursor marketplace that points at Agent Plugin dirs plus `.cursor-plugin` overlays.
- **Users, Codex extras:** same for `.codex-plugin` / `com.openai`.
- **Delete or wrap** flat `skills-install` for cursor/claude/codex skills; a 5-line README is enough.
- **`skills-export` shrinks** to: validate Agent Skills + Agent Plugins manifests, assemble extras, never copy skill bodies three times.
- Claude: skills via Vercel CLI only, unless a real Claude overlay appears.

**Pros:** uses SOTA tools; preserves unique content and extras; stops the redundant installer; Agent Plugins gives Copilot/VS Code/Kiro/Codex/Cursor the portable plugin for free.  
**Cons:** one-time packaging migration; must decide whether `skills/` replaces `core/skills/` or aliases it; Cursor/Codex extras still need overlays because agents cannot share one `agents/` folder (Markdown vs TOML).

### Approach C — Collapse to committed Agent Plugin packages; delete the assembler

Commit one directory per family as an Agent Plugins package with skills inside. No `core/` indirection. No export. Adapters inlined as client extension directories. Landing ingest writes straight into a plugin.

**Pros:** matches how `cursor/plugins` and `vercel-labs/agent-skills` look; zero generate-on-demand.  
**Cons:** larger git trees; harder ingest; Cursor vs Codex agent files still conflict unless extension dirs are actually loaded by those clients (Cursor still documents extras at plugin-root `agents/`, `hooks/`, `rules/` under `.cursor-plugin`). High chance of fighting client loaders.

**Use if:** you are willing to drop Codex/Cursor extras or maintain two committed plugin trees again (the thing #21 just deleted).

---

## 7. Recommended design (Approach B)

### 7.1 Product positioning

This repo is a **portable skill and workflow-plugin catalog**, not a package manager.

README lead should become:

1. Browse plugin families and skills.
2. Install skills: `npx skills add dasobral/skills`.
3. Optional: install Cursor/Codex extras (agents/hooks/rules) with the remaining native installer.

### 7.2 Source of truth

Keep a single skill body per skill. Prefer renaming `core/skills/` → `skills/` (well-known path) **or** keeping `core/skills/` and publishing a generated/symlink `skills/` at repo root for the Vercel CLI. Do not keep two edited copies.

`core/manifest.yaml` remains the family map until each family has an Agent Plugins `plugin.json`. Then the YAML can become generated, or stay as the authoring index that *writes* `plugin.json` files.

### 7.3 Portable plugins

Each family gets an Agent Plugins 1.0.0 package:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "codecraft",
  "version": "2.1.0",
  "description": "End-to-end code quality: analyze, write, review, audit cognitive debt.",
  "license": "MIT",
  "keywords": ["code-quality", "review"]
}
```

Skills live under that plugin’s `skills/` as the grouped view (links or assemble-on-demand). No MCP in v1 of this migration unless a real `mcp.json` exists.

These packages are what Cursor, Codex 0.146+, Copilot, VS Code, and Kiro can load without this repo’s installer.

### 7.4 Client extras (the part Vercel CLI will not do)

Keep adapters. Do not try to unify Cursor Markdown agents and Codex TOML agents in one `agents/` folder.

Preferred overlay policy:

- Cursor extras stay Cursor Plugins: `.cursor-plugin/plugin.json` + `agents/`, `hooks/`, `rules/` in a **Cursor-assembled** tree, or in a Cursor extension namespace if/when Cursor loads `com.anysphere.cursor/` for those components. Until that is documented, keep generating a Cursor plugin tree that *references* the same skill directories rather than copying them.
- Codex extras stay `.codex-plugin/plugin.json` (or `com.openai` on the Agent Plugin) for hooks/interface; agent TOML remains opt-in via `install-plugin-agents`.
- Claude: no overlay until there is real Claude-only content.

### 7.5 Installer policy

| User goal | Command |
| --- | --- |
| Skills in any supported agent | `npx skills add dasobral/skills` |
| Subset of skills | `npx skills add dasobral/skills --skill <name> …` |
| Cursor agents/hooks/rules | keep `./bin/skills-install cursor --plugins` until a marketplace submit path exists |
| Codex hooks/agents | keep `./bin/skills-install codex --plugins` |
| Claude skills | Vercel CLI only |

Remove the default flat mode of `skills-install` (or make it print “use npx skills add” and exit).

### 7.6 Discovery hygiene (do this even if the rest waits)

- Mark or relocate `landing/examples/sample-landing-skill`.
- Mark Codex-only helpers `metadata.internal: true` (Vercel CLI hides these unless `INSTALL_INTERNAL_SKILLS=1`).
- Ensure test fixtures cannot appear in recursive search (already mostly true).
- Put publishable skills on a well-known path so `--full-depth` is unnecessary.

### 7.7 What not to build

- A new skills.sh competitor.
- A fourth plugin format.
- Support for 70 agents inside `skills-install`.
- Agent Plugins extensions for components Cursor/Codex do not actually load from extension directories yet.
- Re-committing three generated `plugins/{cursor,claude,codex}/` skill copies (reverting #21).

### 7.8 Testing implications (when implementation is approved)

- Keep Python tests for validation, ingest, and **extras assembly**.
- Add a contract test: `npx skills add <repo> --list` returns exactly the 26 public core skills (or 26 plus documented internals).
- Add Agent Plugins schema validation for each family `plugin.json`.
- Do not add tests that reimplement Vercel CLI install paths.

---

## 8. Proposed improvements and fixes (implementation backlog)

Priority order if Approach B is approved:

1. **Discovery hygiene** — internal metadata / move sample skill; well-known `skills/` path.
2. **README rewrite** — Vercel CLI as the skill installer; native installer only for extras; honest Claude story.
3. **Agent Plugins manifests** per family (`plugin.json` + grouped `skills/`).
4. **Deprecate flat `skills-install`** — message + exit, then delete.
5. **Shrink `skills-export`** — stop triple-copying skill bodies; assemble extras only.
6. **Optional:** Cursor/Codex marketplace docs for extras; do not invent a new marketplace protocol.
7. **Optional later:** submit Agent Plugins to client marketplaces (Cursor Marketplace, Codex Plugins Directory) once packages are spec-valid.

Fixes that are valid even under Approach A:

- Recursive CLI currently offers a landing example and three Codex-only helpers as if they were portable skills.
- README does not mention the community installer, so users assume this repo is the only way in.
- Claude adapter promises plugins it does not specialize.
- `skills-install` and `npx skills add` will diverge in target paths as Vercel adds agents; maintaining parity is a losing game.

---

## 9. Risks and open points

- **Cursor dual manifest:** a directory with both root `plugin.json` and `.cursor-plugin/plugin.json` may be treated as a Cursor Plugin. Implementation must follow current Cursor loader rules, not guess. If dual-manifest is ambiguous, keep Agent Plugins packages skills-only and assemble a separate Cursor extras tree.
- **Codex overlay precedence:** Codex 0.146 maps Agent Plugins then applies `.codex-plugin` / `com.openai`. Avoid two conflicting sources of truth for `name`/`skills`.
- **Symlinks vs copies:** Vercel CLI prefers symlinks; some environments cannot use them (`--copy`). This repo should not fight that.
- **Plugin grouping in Vercel CLI:** `--skill` is the only subset mechanism. Families are a documentation/packaging concept unless Agent Plugins clients load the plugin as a unit.
- **Telemetry:** Vercel CLI has optional telemetry; mention `DISABLE_TELEMETRY=1` in docs.

No implementation decision is blocked on those except the dual-manifest detail, which is an Approach B task-level check, not a reason to keep the custom skills installer.

---

## 10. Recommendation

**Do not abandon the repo. Abandon the skills-installer identity.**

Approve Approach B unless the only remaining goal is “get these SKILL.md files onto disk,” in which case Approach A plus Vercel CLI is enough and most of `tools/skills-export` can be deleted later.

The work that still matters is the skills, the evidence workflows, and the Cursor/Codex extras. The work that no longer matters is translating `SKILL.md` into three harness folders by hand.
