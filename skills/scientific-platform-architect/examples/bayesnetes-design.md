# Example: Bayesnetes Platform Architecture Design

**Purpose**: Demonstrates correct application of the `scientific-platform-architect`
skill's diagnostic questions, compute layer separation, emulator-first reasoning,
and infrastructure sizing decisions.

---

## Diagnostic Questions

| Question | Answer |
|----------|--------|
| How many concurrent users / institutions? | 1–2 researchers (solo research project) |
| What is the bottleneck — likelihood evaluation or sampling? | Likelihood evaluation: CLASS angular power spectra ~2 s/call |
| What are the data sharing requirements? | Single researcher; files + Git sufficient for chains and configs |
| How often is each kernel called per analysis? | ~100,000 calls per MCMC chain (Cobaya sampler) |

---

## Platform Overview

**Platform name**: Bayesnetes
**Purpose**: Bayesian inference platform for cosmological parameter estimation
from galaxy survey two-point statistics.
**Team size**: 1–2 researchers
**Primary workload**: MCMC sampling of cosmological parameter posteriors

---

## Architecture Diagram (ASCII)

```
Layer 3 — Python Orchestration
  MCP agent (job routing, error diagnosis, posterior interpretation)
    → Python pipeline (Cobaya sampler configuration, chain management)
         ↓
Layer 2 — GPU Operations (PyTorch)
  Angular power spectrum emulator (CLASS → PyTorch MLP)
  Covariance matrix emulator (full → PyTorch MLP)
         ↓
Layer 1 — CPU Kernels (Rust + PyO3)
  fftlog/       ← FFT-based Limber integration
  bessel/       ← Bessel function evaluation (j_ℓ)
  quadrature/   ← Adaptive numerical integration
         ↓
Cobaya MCMC sampler (Python, calls likelihood via Python bindings)
```

---

## Component Table

| Component | Layer | Language / Framework | Call rate / analysis | Purpose |
|-----------|-------|---------------------|---------------------|---------|
| FFTLog kernel | 1 (CPU) | Rust + PyO3 | ~100,000× | Limber integral via FFT; too slow in Python at this rate |
| Bessel kernel | 1 (CPU) | Rust + PyO3 | ~100,000× | j_ℓ(x) evaluation for angular power spectra |
| Quadrature kernel | 1 (CPU) | Rust + PyO3 | ~50,000× | Adaptive integration for projection kernels |
| Angular Cl emulator | 2 (GPU) | PyTorch MLP | ~100,000× | Replaces CLASS calls (2s → 0.2ms, ~10,000×) |
| Covariance emulator | 2 (GPU) | PyTorch MLP | ~10,000× | Replaces full cov computation (5s → 1ms, ~5,000×) |
| Pipeline orchestration | 3 (Orchestration) | Python + Cobaya | — | MCMC configuration, chain management, result I/O |
| MCP agent wrapper | 3 (Agent/MCP) | Python + Agent SDK | — | Job routing, posterior interpretation, convergence flagging |

---

## Emulator Decision

| Observable | Raw evaluation time | MCMC calls required | Emulation verdict |
|-----------|---------------------|--------------------|--------------------|
| Angular power spectra (CLASS) | ~2 s/call | ~100,000 | **Emulate** — ~56 h raw → ~20 s emulated |
| Full covariance matrix | ~5 s/call | ~10,000 | **Emulate** — ~14 h raw → ~10 s emulated |
| Bessel functions (Rust kernel) | ~0.001 ms/call | ~100,000 | **No emulation** — already fast enough |

**Angular Cl emulator design**:

| Property | Value |
|----------|-------|
| Training dataset size | 8,000 simulations (LHS sampling of 5-param ΛCDM prior) |
| Architecture | Fully-connected MLP: 5 → [512, 512, 512] → N_ell |
| Input | (Ωm, Ωb, h, ns, σ8) + nuisance parameters |
| Output | C_ℓ vector (ℓ = 2 to 2000) |
| Validation strategy | Residual plot (<0.1%) + posterior coverage test (50 runs) |
| Estimated training time | ~2 h on RTX 3080 |
| Retraining trigger | Survey mask update, new nuisance parameterisation |

---

## Infrastructure Sizing

| Decision | Choice | Justification |
|----------|--------|--------------|
| Container orchestration | Docker Compose | 1–2 researchers; Kubernetes is ~40 YAML files of unjustified overhead |
| Storage | Files + Git + DVC for chains | No shared mutable state; DVC handles large HDF5 chain files |
| Database | None | Single-researcher workflow; files are sufficient |
| Job scheduler | None (direct execution) | Workloads are sequential per chain; no queuing needed |

**Kubernetes pushback**: A 1–2 researcher project does not justify Kubernetes.
Docker Compose provides the same containerisation with near-zero operational
overhead. Kubernetes would introduce cert management, ingress configuration,
RBAC, and ~40 YAML manifests — consuming more researcher-hours in maintenance
than the compute benefit justifies.

---

## MCP / Agent Integration

| Layer | Responsibility |
|-------|---------------|
| MCP agent | Parse job intent from user prompt; route to correct pipeline configuration; interpret posterior plots; flag convergence failures (Gelman-Rubin R̂ > 1.1) |
| Rust kernels | All FFT, Bessel, and quadrature numerics |
| PyTorch emulators | Angular power spectrum and covariance inference |
| Python pipeline | Cobaya configuration, chain I/O, calling Rust kernels via PyO3 |

**What the agent must NOT do**:
- Call CLASS directly in a loop (route to emulator or pipeline instead)
- Set convergence thresholds without human confirmation
- Modify emulator parameters based on LLM output

---

## Operational Complexity Cost

```
Performance benefit:
  - Angular power spectra: ~10,000× speedup (2 s → 0.2 ms)
  - Covariance matrix: ~5,000× speedup (5 s → 1 ms)
  - Total MCMC chain: ~56 h → ~20 s (100,000 calls × 2 s → emulated)

Operational cost:
  - PyTorch training pipeline: ~1 day to build, ~2 h/month to maintain
  - Model registry (versioned checkpoints + training set metadata): ~0.5 day to set up
  - Coverage validation: ~2 h per emulator deployment
  - Retraining: ~2 h per survey mask or model update
  - Docker Compose services: ~0.5 day to set up, ~1 h/month to maintain

Verdict: Emulators are essential — a 100,000-step MCMC chain takes 56 h without
         them and 20 s with them. The training cost (1 day) is recovered after
         the first chain run.
         Docker Compose is the correct infrastructure choice at this scale.
         Kubernetes would not reduce the computational cost and would add
         significant operational overhead with no benefit for 1–2 users.
```
