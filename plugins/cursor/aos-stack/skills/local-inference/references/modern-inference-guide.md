# Local Inference Reference (2026)

Hardware-agnostic guidance for local LLM inference in agentic workflows.
Detect GPU VRAM at runtime; never hardcode a specific GPU model.

## VRAM Detection

```bash
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
```

Budget formula: `usable_vram = total_gb × 0.90` (reserve 10% for KV cache growth).

## Model Fit Table (approximate weights only)

| Params | FP16 | Q4/AWQ/GPTQ | Notes |
|--------|------|-------------|-------|
| 7–8B | ~14–16 GB | ~4–5 GB | Fits most 8GB+ GPUs at Q4 |
| 14B | ~28 GB | ~8–9 GB | Needs 12GB+ at Q4 for headroom |
| 32B+ | >24 GB | ~18–20 GB | Consumer GPUs: cloud route |
| 70B+ | — | ~40+ GB | Multi-GPU or cloud only |

Add context overhead: ~0.5–2 GB depending on `--max-model-len`.

**Spillage rule:** GPU layers spilling to CPU cause 2–5× latency — treat as
failure for interactive/agentic workloads.

## Backend Selection

| Backend | Use when |
|---------|----------|
| **vLLM** | Tool calling, OpenAI-compatible API, concurrent requests |
| **llama.cpp** | CPU/offline, edge devices, minimal deps |
| **Ollama** | Quick experiments only — warn on multi-step tool loops |

## Modern Model Families (tool-calling)

| Model | Tool calling | Agentic reliability |
|-------|-------------|---------------------|
| Qwen3-8B/14B | Native | Good for ≤3 sequential tool calls |
| Qwen2.5-Coder-14B-AWQ | via vLLM template | Bounded executor tasks |
| Llama 3.x 8B Instruct | Partial | Single-step transforms only |
| DeepSeek-Coder-V2 | Native | Code extraction/generation |

For autonomous multi-step loops (>3 tool calls), route to cloud models
(Claude Opus/Sonnet, GPT-4 class, Composer).

## AOS Routing

```
Cloud orchestrator (reasoning/planning)
  ↓
LiteLLM proxy (OpenAI-format routing)
  ↓
Local executor (atomic, no-reasoning tasks only)
```

Local-eligible tasks: diff application, templated transforms, structured
extraction, lint summaries. NOT: planning, architecture, security review.

See `references/vram-budget.md` and `references/model-registry.md`.
