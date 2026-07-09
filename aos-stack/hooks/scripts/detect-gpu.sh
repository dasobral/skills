#!/usr/bin/env bash
# Check for GPU and suggest local-inference skill when CUDA is available.
set -euo pipefail

if command -v nvidia-smi &>/dev/null; then
  GPU=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1 || echo "unknown")
  echo "{\"continue\": true, \"agentMessage\": \"AOS Stack: GPU detected (${GPU}). Use local-inference skill for vLLM/model selection guidance.\"}"
else
  echo '{"continue": true}'
fi
