# C++ QKD Toolkit

Production-oriented C++ implementation and review workflows for QKD ground-segment and other security-sensitive systems.

## Daily workflow

1. Use `cpp-engineer` to plan and implement against the repository toolchain and runtime constraints.
2. Build and run the repository's tests and analyzers.
3. Apply `cpp-review` with both security and real-time lenses.
4. Resolve blocking findings and preserve the command evidence.

## Triggers

Use for C++ feature work, CMake changes, cryptographic boundaries, concurrency, memory safety, or latency-sensitive paths. The hook emits a bounded security hint on relevant tool activity.

## Required inputs

- Threat model, interfaces, compiler/toolchain, and platform constraints.
- Timing, allocation, concurrency, and failure-handling requirements.
- Diff plus build, sanitizer, static-analysis, and test output.

## Artifacts

- C++ implementation and build changes.
- Reproduction commands and verification evidence.
- Security and real-time review findings with concrete locations.

## Agent authority

The security and real-time reviewers advise independently. They cannot accept risk, certify cryptography, modify scope, or install their templates without explicit user action.

## Deterministic checks and agent decisions

Compilers, tests, sanitizers, analyzers, benchmarks, and the lexical hook produce deterministic observations. Exploitability, deadline risk, and release readiness remain reviewed decisions.

## Data guarantees

The hook inspects relevant tool input, emits context, uses a bounded timeout, and does not modify the project. Reports must distinguish measured results from assumptions.

## Limitations and non-claims

This plugin does not certify QKD security, cryptographic correctness, real-time behavior, memory safety, or production readiness.
