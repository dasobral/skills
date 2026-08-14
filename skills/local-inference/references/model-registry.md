# Model Registry — RTX 3080 / AOS Local Executor

Reference document for the `ml-inference-optimizer` skill.
Lists models validated (or validated-incompatible) for the RTX 3080 / Ubuntu
24.04 / vLLM stack in the AOS architecture.

**Update this file when a new model is tested.**

---

## Model Selection Rules (Summary)

| Task type | Minimum model | Recommended model |
|-----------|--------------|-------------------|
| Single-step extraction, no tool calls | 7–8B Q4 | Qwen3-8B |
| ≤3 sequential tool calls | 14B AWQ | Qwen2.5-Coder-14B-AWQ |
| >3 sequential tool calls | Cloud only | Cloud Opus-level |
| Reasoning / planning | Cloud only | Cloud Opus-level |

---

## Validated Models

### Qwen2.5-Coder-14B-Instruct-AWQ

| Property | Value |
|----------|-------|
| HuggingFace ID | `Qwen/Qwen2.5-Coder-14B-Instruct-AWQ` |
| VRAM (weights) | ~8.5 GB |
| Safe `--max-model-len` | 16384 |
| Native tool calling (Claude Code protocol) | Partial — works with vLLM chat template |
| Tool calling in Ollama | Unreliable — do not use |
| AOS eligibility | Bounded executor tasks, ≤3 tool calls |
| Backend | vLLM only |
| Status | **Recommended primary model** |

### Qwen3-8B

| Property | Value |
|----------|-------|
| HuggingFace ID | `Qwen/Qwen3-8B` |
| VRAM (weights, Q4) | ~5 GB |
| Safe `--max-model-len` | 32768 |
| Native tool calling (Claude Code protocol) | Yes |
| AOS eligibility | Single-step tasks; human orchestration required for multi-step |
| Backend | vLLM (preferred), Ollama (one-shot testing only) |
| Status | **Preferred 8B model for tool-calling tasks** |

### hhao/qwen2.5-coder-tools

| Property | Value |
|----------|-------|
| HuggingFace ID | `hhao/qwen2.5-coder-tools` |
| VRAM (weights, ~8B) | ~5 GB |
| Safe `--max-model-len` | 16384 |
| Native tool calling (Claude Code protocol) | Yes — fine-tuned |
| AOS eligibility | Single-step tasks; human orchestration required for multi-step |
| Backend | vLLM |
| Status | **Fallback if Qwen3-8B unavailable** |

---

## Incompatible / Excluded Models

| Model | Reason |
|-------|--------|
| Qwen2.5-Coder-7B/14B (base, non-instruct, non-AWQ) | Lacks structured tool-call output format. Use AWQ instruct variant. |
| Any 32B+ model | Does not fit in 10 GB VRAM in any quantization. Cloud only. |
| Any 7–8B model in FP16 | ~14–16 GB — does not fit. |
| Any 14B model in FP16 | ~28 GB — does not fit. |

---

## Ollama Compatibility Notes

Ollama may be used for **one-shot, no-tool-call** testing only.

| Scenario | Ollama allowed? |
|----------|----------------|
| Quick one-shot model test | Yes |
| Tool calling, single step | Unreliable — use vLLM |
| Multi-step agentic loops | No — do not use |
| AOS local executor | No — use vLLM always |

> **Mandatory warning** (issue whenever Ollama is proposed for agentic use):
> Ollama has unreliable tool calling in multi-step agentic loops. Function
> call parsing is not model-aware and frequently drops or malforms structured
> outputs across turns. Do not use Ollama as a backend for any workflow
> requiring >1 sequential tool call.

---

## AOS Task Eligibility Checklist

A task is eligible for the local vLLM model **only if all of the following
are true**:

- [ ] No multi-step reasoning required
- [ ] Expressible as a single structured prompt with deterministic output
- [ ] Task type is one of:
  - Applying a diff or patch
  - Templated code transforms (rename, reformat, stub generation)
  - Structured data extraction (JSON/YAML parsing, field extraction)
  - Syntax validation or linting summary generation
- [ ] Requires ≤3 sequential tool calls (14B AWQ) or 0–1 (7–8B)

If **any** item is unchecked → route to cloud orchestrator.
