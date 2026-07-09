# AOS Stack

Agentic orchestration infrastructure: Rust services + local LLM inference.

## Skills

| Skill | Purpose |
|-------|---------|
| `local-inference` | vLLM setup, VRAM budgeting, model selection, LiteLLM config |
| `rust-systems` | Tokio/Axum daemons with OpenAI-compatible APIs |

Modernized from `ml-inference-optimizer` (hardware-adaptive, 2026 model families) and `rust-systems-engineer`.

## Agents

- `inference-advisor` — model/VRAM configuration subagent
- `rust-reviewer` — Rust code review subagent

## Hooks

- `sessionStart` — detects GPU and suggests inference guidance

## Architecture

```
Cloud orchestrator (reasoning) → LiteLLM → local vLLM (atomic tasks)
Rust services implement OpenAI-format API endpoints
```
