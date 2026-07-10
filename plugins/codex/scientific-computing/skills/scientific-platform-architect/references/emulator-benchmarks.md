# Emulator Performance Benchmarks

Reference document for the `scientific-platform-architect` skill.
Benchmarks validated on the Bayesnetes / Kosmonetes platforms.
Use these figures to justify emulator-first decisions.

---

## Validated Speedups

| Observable / Computation | Framework | Raw evaluation | Emulated | Speedup | Notes |
|--------------------------|-----------|----------------|---------|---------|-------|
| Angular power spectra (CLASS) | Python → C++ | ~2 s / call | ~0.2 ms / call | ~10,000× | PyTorch fully-connected emulator |
| Full covariance matrix | Python (NumPy) | ~5 s / call | ~1 ms / call | ~5,000× | PyTorch matmul-based emulator |
| CMB lensing power spectrum | CAMB | ~3 s / call | ~0.5 ms / call | ~6,000× | Transformer backbone |
| Matter power spectrum (linear) | CLASS | ~0.5 s / call | ~0.05 ms / call | ~10,000× | Fully-connected, 3 hidden layers |

---

## MCMC Feasibility Table

| MCMC steps required | Likelihood call time (raw) | Emulator needed? | Estimated wall time (emulated) |
|--------------------|--------------------------|-----------------|-------------------------------|
| 10,000 | < 0.001 s | No | < 10 s |
| 10,000 | 0.1 s | Borderline | ~1 h (raw) → ~2 s (emulated) |
| 10,000 | 1 s | Yes | ~3 h (raw) → ~20 s (emulated) |
| 100,000 | 1 s | Essential | ~28 h (raw) → ~3 min (emulated) |
| 100,000 | 2 s | Essential | ~56 h (raw) → ~6 min (emulated) |

> Rule of thumb: if MCMC requires **>10,000 likelihood calls** and a single
> call takes **>0.1 s**, emulation is almost certainly required.

---

## Emulator Design Defaults

### Training dataset sizes

| Observable type | Recommended training set | Minimum viable |
|----------------|-------------------------|----------------|
| Angular power spectra (5-param ΛCDM) | 5,000–10,000 sims | 2,000 |
| Full covariance matrix | 10,000–20,000 sims | 5,000 |
| Multi-probe joint likelihood | 20,000–50,000 sims | 10,000 |

### Architecture defaults (PyTorch)

| Case | Architecture | Input → Hidden layers → Output |
|------|-------------|-------------------------------|
| Smooth 1D observable (Cl) | Fully-connected (MLP) | N_params → [512, 512, 512] → N_ell |
| 2D covariance matrix | MLP + reshape | N_params → [1024, 1024] → N_bins² |
| High-dimensional parameter space | Transformer encoder | N_params → attention → N_output |

### Validation strategy

1. **Residual plot**: predicted vs. ground-truth on 20% hold-out set.
   Acceptable threshold: residuals < 0.1% over the full parameter prior.

2. **Posterior coverage test**: run MCMC with raw likelihood on 50 test
   points. Compare posteriors from raw vs. emulated likelihood. Require
   <5% shift in mean and <10% shift in width for all parameters.

3. **Training data coverage**: verify the training set covers the full
   prior volume (use LHS or quasi-random sampling, not uniform grid).

---

## Emulator Operational Cost

```
Performance benefit: ~5,000–10,000× speedup on likelihood evaluation
Operational cost:
  - PyTorch training pipeline (training script, data loader, checkpointing)
  - Model registry (versioned checkpoints + training simulation set metadata)
  - Checkpoint validation (coverage test before deployment)
  - Retraining trigger: required whenever the cosmological model or
    survey mask changes
  - Storage: training set + model weights (typically 1–10 GB per emulator)
Verdict: Worth it for MCMC with >50,000 steps.
         Overkill for single-shot Fisher matrix forecasting.
```

---

## When NOT to Emulate

| Scenario | Reason |
|----------|--------|
| Single Fisher matrix computation | One-time evaluation; emulation overhead > benefit |
| Parameter space dimension > 20 | Interpolation accuracy degrades; more training data needed |
| Observable has sharp discontinuities | MLP extrapolation unreliable near discontinuities |
| Training set would cost > 3× the raw computation | Emulation is not cost-effective |
