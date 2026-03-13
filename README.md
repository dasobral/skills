# skills

A collection of Claude Code skills for coding agents. Each skill is a
self-contained directory that can be cloned and dropped into any project's
`.claude/skills/` folder (or `~/.claude/skills/` for personal use).

---

## Installation

```bash
# Clone the repo
git clone <repo-url> skills

# Copy a skill into your project
cp -r skills/<skill-name> /path/to/your/project/.claude/skills/

# Or install personally (available in all projects)
cp -r skills/<skill-name> ~/.claude/skills/
```

Claude Code picks up new skills automatically — no restart needed.

---

## Skills

### [analyze-codebase](./codebase-analysis/)

Analyses a codebase across 16 dimensions — architecture, naming,
formatting, async patterns, error handling, testing, anti-patterns, and
more — then writes a prescriptive `CODING_REQUIREMENTS.md` that future
agent sessions load automatically as hard coding rules.

**Slash command**: `/analyze-codebase [path]`

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition and step-by-step agent instructions |
| `templates/report.md` | Output template with 16 sections |
| `references/analysis-dimensions.md` | Full 16-dimension analysis checklist |

### [cpp-realtime-reviewer](./cpp-realtime-reviewer/)

Reviews production C++ code for real-time embedded and networked systems —
targeting senior engineers working on cryptography, QKD/QRNG, and
satellite-ground secure communication. Checks thread safety, mutex/atomic/
condvar correctness, RAII and resource ownership, latency bottlenecks and
blocking calls in hot paths, and concurrency-safe logging.

Produces a severity-tagged report (**CRITICAL / WARNING / SUGGESTION**) with
inline-annotated code snippets and a summary scorecard.

**Slash command**: `/cpp-realtime-reviewer [path]`

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition and step-by-step agent instructions |
| `references/review-checklist.md` | Full per-domain defect checklist (D1–D5 + QKD/crypto) |
| `references/severity-guide.md` | Severity classification rules |
| `templates/review-report.md` | Structured report template with scorecard and PR checklist |
| `examples/input/websocket_handler.cpp` | Mock concurrent QKD WebSocket handler with intentional defects |
| `examples/output/websocket_handler_review.md` | Reference review output for the example file |

### [agent-orchestrator](./agent-orchestrator/)

Turns Claude into a top-level orchestrator that dynamically deploys specialized
agents (defined as `.md` files in an `agents/` directory) to complete complex,
multi-step tasks. Discovers available agents, decomposes the task into subtasks,
builds a dependency-aware execution plan (task graph), runs agents sequentially
or in parallel, routes named artifacts between them, handles failures with retry
and escalation, and synthesizes a final deliverable.

Agent-definition-agnostic — works with any set of agent definitions, not a
fixed roster.

**Slash command**: `/orchestrate "<task>" [agents-dir]`

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition and step-by-step orchestrator instructions |
| `templates/orchestration-plan.md` | Reusable task-graph plan template (fill in and execute) |
| `references/orchestration-patterns.md` | Pipeline topologies, sequencing rules, routing best practices |
| `examples/agents/` | Three example agent definitions (reader, analyzer, report-writer) |
| `examples/input/architecture.md` | Example input: payment service architecture document |
| `examples/output/plan.md` | Example generated orchestration plan |
| `examples/output/final_report.md` | Example final deliverable (executive summary) |

---

## Skill structure

Every skill in this repo follows the standard Claude Code layout:

```
<skill-name>/
├── SKILL.md                 # Required — frontmatter + agent instructions
├── README.md                # Usage documentation
└── <supporting files>/      # Templates, references, scripts as needed
```

The `name` field in `SKILL.md` frontmatter becomes the `/slash-command`.
