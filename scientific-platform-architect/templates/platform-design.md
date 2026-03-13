# Scientific Platform Architecture Design

<!--
AGENT INSTRUCTIONS
──────────────────
1. Answer the four diagnostic questions (SKILL.md Step 2) before filling
   any section. Do not skip them — the answers determine every major
   architecture decision below.

2. Classify each component into the correct compute layer (Layer 1 / 2 / 3).
   Never blur the boundaries (SKILL.md Step 3).

3. Apply the emulator-first rule (SKILL.md Step 4) before proposing raw
   compute scale-up.

4. Apply the infrastructure sizing rules (SKILL.md Step 5). Push back on
   Kubernetes for ≤3 users.

5. Every proposal must include an Operational Complexity Cost section.
-->

---

## Diagnostic Questions

| Question | Answer |
|----------|--------|
| How many concurrent users / institutions? | {{ANSWER}} |
| What is the bottleneck — likelihood evaluation or sampling? | {{ANSWER}} |
| What are the data sharing requirements? | {{ANSWER}} |
| How often is each kernel called per analysis? | {{ANSWER}} |

---

## Platform Overview

**Platform name**: {{NAME}}
**Purpose**: {{ONE_SENTENCE_DESCRIPTION}}
**Team size**: {{N}} researchers / institutions
**Primary workload**: {{MCMC / Fisher / simulation / other}}

---

## Architecture Diagram (ASCII)

```
{{LAYER_3 — Python orchestration / MCP agents}}
        ↓
{{LAYER_2 — PyTorch GPU ops / emulators}}
        ↓
{{LAYER_1 — Rust CPU kernels (PyO3)}}
        ↓
{{SAMPLER — NumPyro / Cobaya / other}}
```

---

## Component Table

| Component | Layer | Language / Framework | Purpose |
|-----------|-------|---------------------|---------|
| {{KERNEL_NAME}} | 1 (CPU) | Rust + PyO3 | {{DESCRIPTION}} |
| {{EMULATOR_NAME}} | 2 (GPU) | PyTorch | {{DESCRIPTION}} |
| {{PIPELINE_NAME}} | 3 (Orchestration) | Python | {{DESCRIPTION}} |
| {{AGENT_NAME}} | 3 (Agent/MCP) | Python + Agent SDK | {{DESCRIPTION}} |

---

## Emulator Decision

*Apply the emulator-first rule. Fill this section before proposing compute scale-up.*

| Observable | Raw evaluation time | MCMC calls required | Emulation verdict |
|-----------|---------------------|--------------------|--------------------|
| {{OBSERVABLE}} | {{TIME}} | {{N_CALLS}} | {{Emulate / Not needed / Borderline}} |

**Emulator design** (if applicable):

| Property | Value |
|----------|-------|
| Training dataset size | {{N}} simulations |
| Architecture | {{MLP / Transformer / other}} |
| Input dimensionality | {{N_PARAMS}} |
| Output dimensionality | {{N_OUTPUTS}} |
| Validation strategy | Residual plot + posterior coverage test |
| Estimated training time | {{TIME}} on {{HARDWARE}} |
| Retraining trigger | {{CONDITION}} |

---

## Infrastructure Sizing

*Apply the infrastructure sizing rules. Justify every choice.*

| Decision | Choice | Justification |
|----------|--------|--------------|
| Container orchestration | {{Docker Compose / k3s / Kubernetes / bare metal}} | {{JUSTIFICATION}} |
| Storage | {{Files+Git / DVC / NFS / MinIO}} | {{JUSTIFICATION}} |
| Database | {{None / SQLite / PostgreSQL}} | {{JUSTIFICATION}} |
| Job scheduler | {{None / Redis+RQ / SLURM / Ray}} | {{JUSTIFICATION}} |

---

## MCP / Agent Integration

*If applicable. Agents orchestrate; kernels compute.*

| Layer | Responsibility |
|-------|---------------|
| Agent / MCP | {{JOB ROUTING, ERROR DIAGNOSIS, RESULT INTERPRETATION}} |
| Rust kernels | All numerical computation |
| PyTorch ops | Matrix ops, emulator inference |
| Python pipeline | Glue, config, sequencing |

**What agents must NOT do**:
- Call Python numerical code in a loop as a substitute for a compiled kernel
- Make decisions about numerical accuracy or convergence thresholds
- Modify kernel parameters based on LLM output without human confirmation

---

## Operational Complexity Cost

```
Performance benefit: {{QUANTIFIED SPEEDUP OR THROUGHPUT GAIN}}
Operational cost:
  - {{COMPONENT}}: {{MAINTENANCE BURDEN}}
  - {{COMPONENT}}: {{MAINTENANCE BURDEN}}
Verdict: Worth it if {{THRESHOLD CONDITION}}.
         Overkill if {{SIMPLER CONDITION}}.
```

---

## Open Questions / Gaps

List any information that was not provided and is needed to finalise the design:

- [ ] {{GAP_1}}
- [ ] {{GAP_2}}
