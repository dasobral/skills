# VRAM Budget Reference — RTX 3080 (10 GB)

Reference document for the `ml-inference-optimizer` skill.
All figures are validated for an NVIDIA RTX 3080 with 10 GB GDDR6X VRAM
running Ubuntu 24.04.

**Hard ceiling**: 10 GB total VRAM. The GPU driver and CUDA runtime consume
~0.3–0.5 GB at idle. Effective model headroom is ~9.5 GB.

---

## Model VRAM Footprint Table

| Model | Quantization | Weights (VRAM) | KV cache @ 8K ctx | KV cache @ 16K ctx | KV cache @ 32K ctx | Verdict |
|-------|-------------|----------------|--------------------|--------------------|--------------------|---------|
| 7–8B | FP16 | ~14–16 GB | — | — | — | **Does not fit** |
| 7–8B | Q4 / AWQ / GPTQ | ~4–5 GB | ~0.5 GB | ~1 GB | ~2 GB | **Fits** |
| 14B | FP16 | ~28 GB | — | — | — | **Does not fit** |
| 14B | AWQ / GPTQ | ~8–9 GB | ~0.5 GB | ~1 GB | ~1.5 GB | **Fits at ≤16K** |
| 14B | AWQ / GPTQ | ~8–9 GB | — | — | ~1.5 GB | **Spillage risk at 32K** |
| 32B+ | any | >10 GB | — | — | — | **Does not fit** |

> **Spillage hard rule**: GPU layer spillage to CPU RAM causes **2–5× latency
> increase**. Treat spillage as a correctness failure for interactive or
> agentic workloads, not merely a performance concern.

---

## Known Safe Configurations

### Qwen2.5-Coder-14B-AWQ (primary recommended model)

```bash
vllm serve Qwen/Qwen2.5-Coder-14B-Instruct-AWQ \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.90 \
  --tensor-parallel-size 1 \
  --dtype auto \
  --served-model-name qwen25-coder-14b
```

| `--max-model-len` | All layers in VRAM? | Safe for agentic loops? |
|-------------------|---------------------|------------------------|
| 8192 | ✓ Yes | ✓ Yes |
| 16384 | ✓ Yes | ✓ Yes |
| 32768 | ✗ Spillage | ✗ No — 2–5× latency |

### Qwen3-8B (preferred for 8B agentic tasks)

```bash
vllm serve Qwen/Qwen3-8B \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.90 \
  --tensor-parallel-size 1 \
  --dtype auto \
  --served-model-name qwen3-8b
```

| `--max-model-len` | All layers in VRAM? | Safe for agentic loops? |
|-------------------|---------------------|------------------------|
| 32768 | ✓ Yes (at Q4) | Limited — see model selection rules |

### hhao/qwen2.5-coder-tools (tool-calling fine-tune, 8B)

```bash
vllm serve hhao/qwen2.5-coder-tools \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.88 \
  --tensor-parallel-size 1 \
  --dtype auto \
  --served-model-name coder-tools-8b
```

---

## VRAM Diagnosis Commands

```bash
# Snapshot during inference
nvidia-smi --query-gpu=memory.used,memory.free,utilization.gpu \
           --format=csv,noheader,nounits

# Continuous watch (1s interval) — run while sending requests
watch -n 1 nvidia-smi --query-gpu=memory.used,memory.free,utilization.gpu \
                       --format=csv

# Detailed process breakdown
nvidia-smi pmon -s m -d 1

# Check which processes hold VRAM
nvidia-smi --query-compute-apps=pid,used_memory --format=csv
```

---

## KV Cache Size Estimation Formula

```
KV cache per token ≈ 2 × num_layers × num_kv_heads × head_dim × dtype_bytes

For Qwen2.5-14B (approx):
  num_layers = 40, num_kv_heads = 8, head_dim = 128, dtype = fp16 (2 bytes)
  per_token = 2 × 40 × 8 × 128 × 2 = 163,840 bytes ≈ 0.16 MB/token

At 16K context: 16,384 × 0.16 MB ≈ 2.6 GB (batch=1)
At 32K context: 32,768 × 0.16 MB ≈ 5.2 GB (batch=1) → overflow at 14B AWQ
```

> These are approximations. Always verify with `nvidia-smi` during actual
> inference before committing a configuration to production.

---

## Multi-Model Warning

**Never run two models simultaneously on this hardware.**

10 GB VRAM cannot hold two quantized models without severe contention. Use
LRU eviction scheduling via a LiteLLM router instead of concurrent loading.
