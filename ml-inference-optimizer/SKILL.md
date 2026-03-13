---
name: ml-inference-optimizer
description: >
  Assists with local LLM inference setup, configuration, and optimization for
  an NVIDIA RTX 3080 (10GB VRAM) running Ubuntu 24.04. Uses vLLM as the primary
  inference backend and Ollama as a secondary/experimental option. Encodes
  hard-won operational knowledge about VRAM budgeting, context window spillage,
  model selection for agentic tasks, and AOS (Agentic Orchestration System)
  architecture constraints.
  TRIGGER on any mention of: vLLM, Ollama, Modelfile, VRAM, quantization,
  local inference, GPU layers, context window sizing, model selection for
  tool-calling, LiteLLM proxy configuration, or AOS local executor setup.
  ALSO TRIGGER via /ml-inference-optimizer slash command.
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# ML Inference Optimizer Skill

Provide expert guidance on local LLM inference for an **NVIDIA RTX 3080
(10GB VRAM) / Ubuntu 24.04** system running **vLLM** as the primary backend.
Every recommendation must account for the hard VRAM ceiling, GPU layer
spillage risk, and the AOS architecture's requirement that local models only
handle atomic, no-reasoning tasks.

---

## Step 1 — Identify the Request Type

Classify the user's request into one of these categories before proceeding:

| Category | Examples |
|----------|---------|
| **Model selection** | "Which model should I run?", "Will X fit?", "Best model for tool calling?" |
| **Backend setup** | vLLM install/config, Ollama Modelfile, LiteLLM proxy wiring |
| **VRAM / context sizing** | Context window tuning, `--max-model-len`, GPU layer count |
| **Agentic task routing** | Deciding local vs. cloud for a given task or tool-call depth |
| **Troubleshooting** | Latency spikes, OOM errors, broken tool calls in loops |

State the identified category before responding. If multiple categories
apply, address them in the order listed above.

---

## Step 2 — Apply the VRAM Budget Check

**Always run this check before recommending any model or configuration.**

### VRAM envelope rules (RTX 3080 / 10GB)

| Model size | Quantization | Approx. VRAM (weights only) | Context overhead | Verdict |
|------------|-------------|----------------------------|-----------------|---------|
| 7–8B | FP16 | ~14–16 GB | — | **Does not fit** |
| 7–8B | Q4/AWQ/GPTQ | ~4–5 GB | ~1–2 GB @ 8K ctx | **Fits** |
| 14B | FP16 | ~28 GB | — | **Does not fit** |
| 14B | AWQ/GPTQ | ~8–9 GB | ~0.5 GB @ 16K ctx | **Fits at 16K** |
| 14B | AWQ/GPTQ | ~8–9 GB | ~1.5 GB @ 32K ctx | **Spillage risk** |
| 32B+ | any | >10 GB | — | **Does not fit** |

### Spillage hard rule

> GPU layer spillage to CPU RAM causes **2–5× latency increase**. Treat
> spillage as a correctness failure for interactive or agentic workloads,
> not merely a performance concern.

**Known safe configuration — Qwen2.5-Coder-14B-AWQ:**
- `--max-model-len 16384` → all layers fit in VRAM ✓
- `--max-model-len 32768` → spillage occurs — do **not** use for agentic loops

If the user has not specified `--max-model-len`, recommend 16K as the default
for any 14B AWQ model on this hardware. Explicitly warn if they request 32K+.

---

## Step 3 — Apply Backend Selection Rules

### vLLM (primary — prefer always for agentic use)

Use vLLM when:
- The workload involves tool calling, function calling, or multi-step agent loops
- Proper chat template rendering is required (vLLM is model-aware)
- An OpenAI-compatible API endpoint is needed (`/v1/chat/completions`)
- Throughput or concurrent request handling matters

Recommended launch pattern:
```bash
vllm serve <model-id-or-path> \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.90 \
  --tensor-parallel-size 1 \
  --dtype auto \
  --served-model-name <alias>
```

Key flags to always include:
- `--max-model-len` — never omit; defaults can exceed VRAM budget
- `--gpu-memory-utilization 0.90` — leaves headroom for KV cache growth
- `--dtype auto` — respects quantization embedded in the model config

### Ollama (secondary — experimentation only)

Use Ollama only when:
- Quick one-shot testing of a new model
- No tool calling is required
- The user explicitly prefers Ollama's UX

**Mandatory warning to issue whenever Ollama is recommended for agentic use:**

> WARNING: Ollama has unreliable tool calling in multi-step agentic loops.
> Function call parsing is not model-aware and frequently drops or
> malforms structured outputs across turns. Do not use Ollama as a
> backend for any workflow requiring >1 sequential tool call.

### Multi-model setups

**Never run multiple models simultaneously on this hardware.** 10GB VRAM
cannot hold two quantized models without severe contention.

Use **LRU eviction scheduling** instead:
- Load the requested model on demand, evict the least-recently-used model
- vLLM does not support hot-swapping natively; use a supervisor script or
  a LiteLLM router with `model_list` and `routing_strategy: least-busy`
  to serialize requests across a single GPU slot

---

## Step 4 — Apply Model Selection Rules for Agentic Tasks

### Size vs. reliability threshold

| Model size | Autonomous tool-calling | Recommended use |
|------------|------------------------|----------------|
| 7–8B | **Unreliable** — requires human orchestration between steps | Single-step extraction, templated transforms |
| 14B (AWQ) | Reliable for ≤3 sequential tool calls | Bounded executor tasks |
| 32B+ | Reliable for complex chains | Cloud-only on this hardware |

> Rule of thumb: if a task requires **>3 sequential tool calls**, route to
> a cloud model (Opus-level). Do not attempt to compensate with prompt
> engineering on a local 8B model.

### Tool-calling model compatibility

| Model | Native tool calling for Claude Code protocol | Notes |
|-------|---------------------------------------------|-------|
| Qwen2.5-Coder (base) | **No** | Lacks structured tool-call output format |
| Qwen3-8B | Yes | Preferred for 8B agentic tasks |
| hhao/qwen2.5-coder-tools | Yes | Fine-tuned variant; use if Qwen3-8B is unavailable |
| Qwen2.5-Coder-14B-AWQ | Partial | Works with vLLM's chat template; unreliable in Ollama |

When the user asks about running Qwen2.5-Coder variants for tool-calling
agent tasks, always recommend the `hhao/qwen2.5-coder-tools` fine-tune or
Qwen3-8B over the base Qwen2.5-Coder models.

---

## Step 5 — Apply AOS Architecture Constraints

This system uses an **AOS (Agentic Orchestration System)** architecture:

```
Cloud Orchestrator (Opus-level)
  ↓  reasons, plans, decomposes tasks
LiteLLM Proxy  ←→  OpenAI-format API
  ↓  routes to model by alias
Local vLLM endpoint  (RTX 3080)
  ↓  bounded executor — no reasoning
Atomic task output  →  returned to orchestrator
```

### Local model task eligibility

A task is eligible for the local model **only if all of the following are true**:

1. The task requires **no multi-step reasoning** (no chain-of-thought needed)
2. The task can be expressed as a **single structured prompt** with a deterministic output format
3. The task falls into one of these categories:
   - Applying a diff or patch
   - Templated code transforms (rename, reformat, stub generation)
   - Structured data extraction (JSON/YAML parsing, field extraction)
   - Syntax validation or linting summary generation

If the task requires reasoning, planning, or >3 tool calls, it **must** be
routed to the cloud orchestrator. Do not suggest "trying the local model
first" for reasoning-heavy tasks — the failure mode is silent degradation,
not an error.

### LiteLLM proxy wiring

When helping configure LiteLLM for this architecture, always include:

```yaml
model_list:
  - model_name: local-coder        # alias used by orchestrator
    litellm_params:
      model: openai/<vllm-served-model-alias>
      api_base: http://localhost:8000/v1
      api_key: "none"
      max_tokens: 4096

router_settings:
  routing_strategy: least-busy
  num_retries: 2
  timeout: 30
```

Key points:
- Use `openai/<alias>` prefix so LiteLLM treats the vLLM endpoint as an
  OpenAI-compatible provider
- Set `timeout: 30` — local models under VRAM pressure can stall; the
  orchestrator should fail fast and re-route rather than blocking

---

## Step 6 — Troubleshoot Common Failure Modes

If the user reports a problem, map it to a root cause before suggesting fixes:

| Symptom | Most likely cause | First check |
|---------|------------------|-------------|
| Latency 2–5× worse than expected | GPU layer spillage | `nvidia-smi` during inference; check `--max-model-len` |
| OOM crash on vLLM startup | VRAM budget exceeded | Reduce `--max-model-len` or switch to more aggressive quantization |
| Tool calls missing or malformed | Wrong model / backend | Check model has tool-call fine-tuning; confirm using vLLM not Ollama |
| Tool calls work for step 1–2, fail at step 3+ | 8B model reliability limit | Route task to cloud or use 14B AWQ model |
| Model loads but outputs garbage | `--dtype` mismatch with quantization | Add `--dtype auto` or match dtype to model's quant format |
| LiteLLM returns 500 on local route | vLLM not running or wrong port | `curl http://localhost:8000/v1/models` to verify endpoint |

For each troubleshooting scenario, always run `nvidia-smi` output diagnostics
as a first step:

```bash
# Check VRAM usage during inference
watch -n 1 nvidia-smi --query-gpu=memory.used,memory.free,utilization.gpu --format=csv
```

---

## Skill Rules

- **VRAM first.** Every model or config recommendation must be preceded by
  an explicit VRAM budget calculation. Never recommend a model without
  confirming it fits within 10GB including KV cache.
- **Spillage is a hard failure.** Never suggest a configuration that causes
  GPU layer spillage for agentic workloads. If the user insists, document
  the 2–5× latency penalty explicitly.
- **vLLM over Ollama for anything agentic.** Always prefer vLLM. When
  Ollama is mentioned for tool-calling use, issue the mandatory warning in
  Step 3 before any other guidance.
- **8B models need human orchestration.** Do not present 8B models as viable
  for autonomous multi-step tool-call loops. Recommend them only for
  single-step, human-supervised tasks.
- **AOS task routing is non-negotiable.** If a task requires reasoning,
  route it to the cloud orchestrator. Do not suggest workarounds that
  offload reasoning to the local model.
- **Qwen2.5-Coder base ≠ tool-calling.** Always flag that base
  Qwen2.5-Coder models lack the Claude Code tool-call protocol. Redirect
  to Qwen3-8B or hhao/qwen2.5-coder-tools.
- **Cite concrete numbers.** Use specific VRAM figures, context lengths,
  and latency multipliers (not vague terms like "might be slow").
- **Never modify source files.** This skill advises only. Write config
  files only when the user explicitly requests it.
