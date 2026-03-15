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

### [agent-creator](./agent-creator/)

Scaffolds a new Claude agent definition file (`.md`) for use inside a
skill's `agents/` directory or as a standalone component in a multi-agent
system. Guides the user through six definition layers — Role, Inputs,
Process, Output contract, Constraints, and Integration hooks — then
writes a complete, ready-to-use `{agent-name}.md` file.

**Slash command**: `/create-agent [agent-name] [output-path]`

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition and step-by-step scaffolding instructions |
| `templates/agent-definition.md` | Reusable agent definition template |
| `references/agent-conventions.md` | Naming, structure, and integration conventions |
| `examples/summarizer.md` | Example agent definition (document summarizer) |

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

### [career-document-writer](./career-document-writer/)

Assists in writing and editing professional career documents — CVs, cover
letters, research statements, fellowship proposals, and resignation letters.
Maintains awareness of the tension between academic and industry positioning,
translates research into engineering competencies for industrial roles, tracks
character/word counts against submission limits, and never invents credentials.

**Slash command**: `/career-document-writer`

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition and writing instructions |
| `templates/cover-letter.md` | Cover letter template |
| `templates/cv-latex.tex` | LaTeX CV template |
| `references/profile.md` | Career profile and positioning reference |
| `examples/cover-letter-esa-euroqci.md` | Example cover letter (ESA EuroQCI application) |

### [cognitive-debt](./cognitive-debt/)

Analyses a codebase (or a specified subset) for accumulated cognitive load —
the mental effort required to read, understand, and modify code. Identifies
seven debt categories: dead code, over-engineering, duplication, abstraction
quality, control flow complexity, naming, and test debt. Applies per-language
heuristics for Python, TypeScript/JS, Rust, C++, and Go. Scales analysis depth
to codebase size (exhaustive for <500 LOC, structural + sampled for larger).
Writes `COGNITIVE_DEBT.md` with a severity table (🔴/🟡/🟢), per-finding
evidence, actionable recommendations, a prioritized action list, and a
"what's working well" section. Complements `analyze-codebase` (structure and
dependencies) and `code-quality-reviewer` (correctness and security).

**Slash command**: `/cognitive-debt [path]`

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition and step-by-step analysis instructions |
| `references/debt-categories.md` | Seven debt categories with per-language heuristics and calibrated thresholds |
| `references/judgment-guidelines.md` | When not to flag — intentional design, language idioms, uncertainty handling |
| `templates/COGNITIVE_DEBT.md` | Structured report template with severity table, findings, and action list |

### [code-quality-reviewer](./code-quality-reviewer/)

Performs a language-agnostic code review across four pillars — Clarity,
Simplicity, Good Practices, and Security — targeting experienced engineers
who want a second pair of eyes on code health rather than functional
correctness. Produces a structured report with severity-tagged findings
(**CRITICAL / WARNING / SUGGESTION**) and concrete fix suggestions.

**Slash command**: `/code-quality-reviewer [path]`

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition and review instructions |
| `templates/review-report.md` | Structured four-pillar report template |
| `references/review-checklist.md` | Per-pillar defect checklist |
| `examples/input/user_service.py` | Example Python service with intentional issues |
| `examples/output/user_service_review.md` | Reference review output for the example |

### [cpp-production-engineer](./cpp-production-engineer/)

Assists with production-grade C++ development in industrial/defense software
contexts. Enforces thread-safe singleton patterns, strict RAII with smart
pointers, syslog-compatible structured logging (never logging key material),
websocketpp + Boost.Asio TLS networking with reconnect logic, and CMake
target-based build organisation. Checks C++17 compatibility before suggesting
any pattern and reasons explicitly about mutex ownership.

**Slash command**: `/cpp-production-engineer`

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition and coding standards |
| `references/coding-standards.md` | Detailed C++ standards and patterns reference |
| `templates/CMakeLists-root.txt` | CMake root template with target-based layout |
| `templates/Jenkinsfile.groovy` | CI pipeline template |
| `examples/input/ws_client.cpp` | Example WebSocket client with issues |
| `examples/output/ws_client_review.md` | Reference review output for the example |

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

### [ml-inference-optimizer](./ml-inference-optimizer/)

Assists with local LLM inference setup, configuration, and optimization for
an NVIDIA RTX 3080 (10 GB VRAM) running Ubuntu 24.04. Uses vLLM as the
primary backend and Ollama as a secondary option. Encodes operational knowledge
about VRAM budgeting, context window spillage, model selection for agentic
tasks, and AOS (Agentic Orchestration System) architecture constraints.

**Slash command**: `/ml-inference-optimizer`

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition and optimization instructions |
| `references/model-registry.md` | Curated model list with VRAM requirements |
| `references/vram-budget.md` | VRAM budgeting rules and spillage thresholds |
| `templates/litellm-config.yaml` | LiteLLM proxy configuration template |
| `templates/vllm-launch.sh` | vLLM launch script template |

### [qkd-security-engineer](./qkd-security-engineer/)

Assists engineers working on Quantum Key Distribution (QKD) systems,
specifically classical ground segment software. Covers QKD protocol context
(BB84, key sifting, error correction, privacy amplification, QBER thresholds),
classical channel security, key management, and ETSI QKD standards (GS QKD 004,
GS QKD 014, EuroQCI architecture). Flags unauthenticated messages, key material
in logs, missing zeroization, and nonce/IV reuse.

**Slash command**: `/qkd-security-engineer`

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition and security review instructions |
| `references/etsi-standards.md` | ETSI QKD standards reference (GS QKD 004, 014) |
| `templates/security-review-report.md` | Security review report template |
| `examples/input/key_manager.cpp` | Example KMS component with security issues |
| `examples/output/key_manager_review.md` | Reference security review output |

### [rust-systems-engineer](./rust-systems-engineer/)

Guides coding agents working on Rust-based systems projects — daemons, HTTP
APIs, orchestrators, and AOS components. Enforces async-first architecture
with Tokio and Axum, LiteLLM-compatible OpenAI-format APIs, strong typing,
explicit error propagation, modular workspace layouts, and systemd-compatible
daemon design (structured logs, graceful shutdown, health endpoints). Audits
`Cargo.toml` before suggesting any dependency.

**Slash command**: `/rust-systems-engineer`

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition and coding standards |
| `references/crate-selection-guide.md` | Approved crates with justifications |
| `templates/Cargo-workspace.toml` | Workspace manifest template |
| `examples/input/service.rs` | Example Rust service with issues |
| `examples/output/service_review.md` | Reference review output for the example |

### [scientific-platform-architect](./scientific-platform-architect/)

Assists in designing and building scientific computing platforms that combine
high-performance compute kernels with modern infrastructure. Encodes
architectural decisions from real platform design for cosmological Bayesian
inference. Enforces compute layer separation (Rust CPU kernels / PyTorch-GPU /
Python orchestration), emulator-first thinking, and right-sized infrastructure.
Pushes back on over-engineered infrastructure for solo or small-team research.

**Slash command**: `/scientific-platform-architect`

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition and architecture instructions |
| `references/emulator-benchmarks.md` | Neural emulator performance benchmarks |
| `references/infrastructure-decision-guide.md` | When to use Kubernetes vs. simpler alternatives |
| `templates/platform-design.md` | Platform design document template |
| `examples/bayesnetes-design.md` | Example platform design (Bayesian inference) |

### [style-conformant-coder](./style-conformant-coder/)

Writes code — in any language — that exactly matches the project's established
style and conventions. Reads the codebase before writing a single line, infers
naming, formatting, error handling, and structure conventions from existing
code, and produces output that looks like it was written by a senior engineer
already on the team. Sits at the centre of a three-skill pipeline:
`analyze-codebase → style-conformant-coder → code-quality-reviewer`.

**Slash command**: `/style-conformant-coder`

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition and style-inference instructions |
| `references/default-style.md` | Fallback style guide when no codebase context exists |
| `references/pipeline-integration.md` | How this skill fits into the three-skill pipeline |
| `references/task-patterns.md` | Common task patterns and how to handle each |

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
