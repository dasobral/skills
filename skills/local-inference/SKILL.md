---
name: local-inference
description: >
  Local LLM inference setup and optimization for agentic workflows. vLLM
  primary backend, hardware-adaptive VRAM budgeting, model selection for
  tool-calling, LiteLLM proxy wiring, and AOS task-routing policy.
  Part of AOS Stack plugin. Use for vLLM, VRAM, quantization, model
  selection, LiteLLM config, or local executor setup.
---

# Local Inference

Expert guidance on local LLM inference for agentic orchestration systems.

## Step 1 — Classify Request

| Category | Examples |
|----------|----------|
| Model selection | Which model fits? Best for tool calling? |
| Backend setup | vLLM install, LiteLLM proxy |
| VRAM sizing | Context window, quantization trade-offs |
| Task routing | Local vs cloud for a workload |
| Troubleshooting | OOM, malformed tool calls, latency spikes |

## Step 2 — Detect Hardware

Run `nvidia-smi` (or ask user for VRAM budget). Read
`references/modern-inference-guide.md` and `references/vram-budget.md`.

Never recommend a model without explicit VRAM calculation including KV cache.

## Step 3 — Backend Rules

- **vLLM** for anything agentic (tool calling, multi-turn)
- **Ollama** for experiments only — warn on unreliable tool loops
- Never run multiple large models simultaneously on one GPU

Recommended vLLM launch:
```bash
vllm serve <model> \
  --max-model-len <fit-to-vram> \
  --gpu-memory-utilization 0.90 \
  --dtype auto \
  --served-model-name <alias>
```

## Step 4 — Model Selection

Use `references/model-registry.md`. Key rules:
- 8B models: single-step or human-supervised only
- 14B Q4: reliable for ≤3 sequential tool calls
- Reasoning/planning: cloud orchestrator (Opus/Sonnet/Composer class)

## Step 5 — AOS Integration

LiteLLM config template: `templates/litellm-config.yaml`
Launch script: `templates/vllm-launch.sh`

Local tasks must be atomic with deterministic output — no chain-of-thought.

## Step 6 — Troubleshoot

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| 2–5× latency | GPU spillage | Reduce `--max-model-len` |
| OOM on startup | VRAM exceeded | Smaller quant or shorter context |
| Malformed tools | Wrong model/backend | vLLM + tool-tuned model |
| Tools fail at step 3+ | Model too small | Route to cloud |

## Rules

- VRAM first — cite concrete numbers
- Spillage is hard failure for agentic workloads
- Pair with `rust-systems` for LiteLLM-compatible API implementation
