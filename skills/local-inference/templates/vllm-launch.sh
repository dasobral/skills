#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# vLLM Launch Script — RTX 3080 / Ubuntu 24.04
# Template for the ml-inference-optimizer skill.
#
# Usage:
#   ./vllm-launch.sh [14b|8b|tools]
#   ./vllm-launch.sh  (defaults to 14b)
#
# Rules encoded:
#   --max-model-len is ALWAYS specified (never omit — default can exceed VRAM)
#   --gpu-memory-utilization 0.90 leaves headroom for KV cache growth
#   --dtype auto respects quantization in model config
#   --tensor-parallel-size 1 for single GPU
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

MODEL_VARIANT="${1:-14b}"

case "${MODEL_VARIANT}" in

  14b)
    # Qwen2.5-Coder-14B-AWQ — primary model, ≤3 tool calls, 16K context
    # SAFE: all layers fit in VRAM at max-model-len 16384
    # WARNING: 32768 causes GPU layer spillage — do NOT use for agentic loops
    exec vllm serve "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ" \
      --max-model-len 16384 \
      --gpu-memory-utilization 0.90 \
      --tensor-parallel-size 1 \
      --dtype auto \
      --served-model-name qwen25-coder-14b \
      --host 127.0.0.1 \
      --port 8000
    ;;

  8b)
    # Qwen3-8B — preferred 8B model for tool-calling tasks
    # Fits at 32K context in Q4; human orchestration required for multi-step
    exec vllm serve "Qwen/Qwen3-8B" \
      --max-model-len 32768 \
      --gpu-memory-utilization 0.90 \
      --tensor-parallel-size 1 \
      --dtype auto \
      --served-model-name qwen3-8b \
      --host 127.0.0.1 \
      --port 8000
    ;;

  tools)
    # hhao/qwen2.5-coder-tools — tool-call fine-tune, fallback if Qwen3-8B unavailable
    exec vllm serve "hhao/qwen2.5-coder-tools" \
      --max-model-len 16384 \
      --gpu-memory-utilization 0.88 \
      --tensor-parallel-size 1 \
      --dtype auto \
      --served-model-name coder-tools-8b \
      --host 127.0.0.1 \
      --port 8000
    ;;

  *)
    echo "ERROR: Unknown model variant '${MODEL_VARIANT}'"
    echo "Usage: $0 [14b|8b|tools]"
    exit 1
    ;;
esac

# ── Post-launch verification (run in a separate terminal) ─────────────────────
#
#   # Verify the endpoint is up
#   curl -s http://localhost:8000/v1/models | python3 -m json.tool
#
#   # Check VRAM usage during inference
#   watch -n 1 nvidia-smi --query-gpu=memory.used,memory.free,utilization.gpu \
#                          --format=csv
#
#   # Test a completion
#   curl -s http://localhost:8000/v1/chat/completions \
#     -H "Content-Type: application/json" \
#     -d '{"model": "qwen25-coder-14b", "messages": [{"role": "user", "content": "Hello"}]}' \
#     | python3 -m json.tool
