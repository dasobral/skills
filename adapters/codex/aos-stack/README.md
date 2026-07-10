# AOS Stack

Rust service and local-inference workflows for LiteLLM-compatible agentic orchestration systems.

## Daily workflow

1. Use `local-inference` to inventory hardware, model, serving, and compatibility requirements.
2. Use `rust-systems` to implement or review the service boundary.
3. Run formatting, compilation, tests, and representative inference probes.
4. Compare measured resource use and API behavior with the acceptance criteria.

## Triggers

Use for Rust/Tokio services, LiteLLM-compatible APIs, vLLM deployment, model selection, GPU capacity planning, or inference reliability. The session hook reports available NVIDIA GPU context.

## Required inputs

- API contract, model and tokenizer identity, workload, and latency targets.
- Hardware/VRAM, runtime, deployment, concurrency, and failure constraints.
- Rust diff plus build, test, and inference measurements.

## Artifacts

- Inference deployment plan and compatibility findings.
- Rust implementation or review report.
- Reproduction commands, measured capacity, and unresolved operational risks.

## Agent authority

The inference advisor and Rust reviewer provide recommendations only. They cannot reserve infrastructure, select production models, accept operational risk, or install themselves.

## Deterministic checks and agent decisions

Compilation, tests, API probes, GPU discovery, and measurements are deterministic observations. Architecture, model suitability, capacity margin, and operational priority are agent judgments.

## Data guarantees

The GPU hook invokes a bounded local capability query, emits context, and does not write project files. Measurements must identify their environment and must not be presented as universal benchmarks.

## Limitations and non-claims

This plugin does not guarantee throughput, latency, model quality, API compatibility, memory safety, or production reliability.
