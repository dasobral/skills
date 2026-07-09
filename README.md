# Cursor Skills Marketplace

A multi-plugin marketplace for Cursor: consolidated agent skills, subagents,
rules, and hooks — modernized from a collection of standalone Claude Code skills.

**13 legacy skills → 6 focused plugins**

## Plugins

| Plugin | Skills | What it does |
|--------|--------|--------------|
| [**codecraft**](./codecraft/) | 4 | Analyze conventions, write conformant code, review quality, audit cognitive debt |
| [**cpp-qkd-toolkit**](./cpp-qkd-toolkit/) | 2 | Production C++ for QKD/defense — implement and multi-lens review |
| [**agent-platform**](./agent-platform/) | 2 | Create agent definitions and orchestrate multi-agent pipelines |
| [**aos-stack**](./aos-stack/) | 2 | Rust AOS services + local LLM inference (vLLM, LiteLLM) |
| [**scientific-computing**](./scientific-computing/) | 1 | Scientific platform architecture and infrastructure sizing |
| [**career-writer**](./career-writer/) | 1 | Career documents with audience-aware framing |

## Installation

### Marketplace (all plugins)

Add this repository as a Cursor marketplace, then install individual plugins
from the Customize page.

### Single plugin (local)

```bash
# Clone and install one plugin locally
git clone <repo-url> skills
cp -r skills/codecraft ~/.cursor/plugins/local/codecraft
```

Plugins are immediately available in Cursor after install.

## Consolidation Map

Legacy standalone skills were merged to eliminate redundancy:

| Legacy skill(s) | New plugin | New skill |
|-----------------|------------|-----------|
| `codebase-analysis` | codecraft | `analyze-codebase` |
| `style-conformant-coder` | codecraft | `write-conformant-code` |
| `code-quality-reviewer` + `cognitive-debt` | codecraft | `review-quality` + `audit-cognitive-debt` (shared heuristics) |
| `cpp-production-engineer` + `cpp-realtime-reviewer` + `qkd-security-engineer` | cpp-qkd-toolkit | `cpp-engineer` + `cpp-review` (lens modes) |
| `agent-creator` + `agent-orchestrator` | agent-platform | `create-agent` + `orchestrate` |
| `ml-inference-optimizer` + `rust-systems-engineer` | aos-stack | `local-inference` + `rust-systems` |
| `scientific-platform-architect` | scientific-computing | `scientific-platform-architect` |
| `career-document-writer` | career-writer | `career-documents` |

## Recommended Workflows

### Code quality pipeline

```
analyze-codebase → write-conformant-code → review-quality → audit-cognitive-debt
```

### C++ QKD development

```
cpp-engineer (implement) → cpp-review --full (audit)
```

### Multi-agent task

```
create-agent (define) → orchestrate (execute with Task tool parallelism)
```

### AOS local stack

```
local-inference (pick model) → rust-systems (wire API) → orchestrate (run agents)
```

## Plugin Structure

Each plugin follows the Cursor plugin format:

```
<plugin>/
├── .cursor-plugin/plugin.json   # Manifest
├── skills/<name>/SKILL.md       # Agent skills
├── agents/*.md                  # Subagent definitions
├── rules/*.mdc                  # Cursor rules (optional)
├── hooks/hooks.json             # Lifecycle hooks (optional)
└── README.md
```

## Modernization (v2.0)

- **Cursor-native**: `.cursor/` paths, `AGENTS.md` wiring, Task tool subagents
- **Hardware-adaptive**: local inference detects GPU VRAM instead of hardcoding RTX 3080
- **Model-current**: Qwen3, Llama 3.x, cloud routing for multi-step tool loops
- **Deduplicated**: shared review heuristics, unified C++ review lenses
- **Generalized**: career writer uses fill-in profile template

## License

MIT — see [LICENSE](./LICENSE).
