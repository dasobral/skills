# Infrastructure Decision Guide

Reference document for the `scientific-platform-architect` skill.
Use this guide to determine the appropriate infrastructure for a scientific
computing platform based on team size, concurrency, and data sharing needs.

---

## Primary Decision Tree

```
Step 1: How many concurrent users / institutions?

  ≤ 3 users (solo or small team)
  └─ Step 2: Are workloads >24h or require preemption?
       ├─ No  → STOP. Use bare metal or Docker Compose.
       │        No scheduler needed.
       └─ Yes → Step 3: Is the team willing to operate a scheduler?
                    ├─ Yes → Consider Ray or SLURM (not Kubernetes)
                    └─ No  → Use a job queue (Redis + RQ, or Celery)

  4–9 users, single institution
  └─ Docker Compose + shared NFS volume.
     Add a job queue (Redis + Celery) if workloads need queuing.
     Kubernetes is NOT justified.

  10–50 users, single institution
  └─ Kubernetes is justifiable.
     Use k3s (lightweight) or kind (dev/CI).
     Minimise YAML surface area — avoid Helm until complexity demands it.

  50+ users or multi-institution
  └─ Full Kubernetes with:
       - Namespace isolation per group/institution
       - RBAC for project-level access control
       - Shared storage: Rook/Ceph or NFS with PVCs
       - Auth: OAuth2 + JupyterHub or custom identity provider
       - Monitoring: Prometheus + Grafana
```

---

## Kubernetes Pushback Script

When someone proposes Kubernetes for ≤3 users, respond with this argument:

> "Kubernetes introduces approximately 40–80 YAML manifests (Deployments,
> Services, ConfigMaps, Secrets, Ingress, PersistentVolumeClaims, RBAC roles,
> NetworkPolicies), a control plane to maintain, TLS certificate management
> (cert-manager), ingress configuration (nginx/traefik), and significant
> debugging overhead. For a solo or ≤3-person research project, the
> operational burden will consume more researcher-hours than the compute
> savings justify. Use Docker Compose."

---

## Database Decision Rule

Add a database only if **multiple users need shared mutable state**.

| Use case | Recommendation |
|----------|---------------|
| Single researcher, pipeline outputs | Files + Git. DVC for large binaries. |
| Single researcher, job tracking | SQLite (single file, zero administration). |
| 2–5 researchers, shared chains/jobs | PostgreSQL (single instance, Docker). |
| Multi-institution shared parameter catalogue | Object store (MinIO / S3) + metadata DB (PostgreSQL). |
| Multi-institution real-time streaming | Message bus (Kafka / RabbitMQ) — only if event-driven architecture is required. |

**Never propose**: Cassandra, CockroachDB, or distributed databases for
scientific platforms unless the data volume and write concurrency explicitly
require it (document the throughput numbers that justify the choice).

---

## Storage Decision Rule

| Data type | Storage recommendation |
|-----------|----------------------|
| Code, configs, small parameter files | Git |
| Large simulation outputs (>100MB per file) | DVC (Git LFS alternative with remote backends) |
| Shared read-only datasets (surveys, masks) | Network filesystem (NFS) or object store |
| Model weights / emulator checkpoints | Object store (MinIO) with versioning |
| Intermediate MCMC chains | Files (HDF5 or FITS); database only if joint access needed |

---

## Compute Layer Decision

| Task | Language | Framework | Rationale |
|------|----------|-----------|-----------|
| Inner loop called >1000× per analysis | Rust | PyO3 bindings | Python overhead dominates at this call rate |
| GPU matrix ops, autodiff | Python | PyTorch | Batched parallelism; superior ecosystem |
| GPU ops requiring custom differentiable kernels | Python | JAX | XLA custom call for differentiable Rust kernels |
| Pipeline orchestration, job routing | Python | Native + asyncio | Calling compiled layers; no numerical work here |
| MCP / agent wrappers | Python | Agent SDK | Routing and interpretation only |

**Rust for inner loops rule**: If a kernel is called >1000× per analysis and
is implemented in Python without dispatching to Rust or PyTorch, flag it as a
**CRITICAL** architectural violation in code review.

---

## Operational Complexity Cost Framework

Every architecture proposal must include an explicit cost estimate. Template:

```
Performance benefit: <<quantified speedup or throughput gain>>
Operational cost:
  - <<component 1>>: <<maintenance burden in researcher-hours/month>>
  - <<component 2>>: ...
Verdict: Worth it if <<threshold condition>>.
         Overkill if <<simpler condition>>.
```

Example:
```
Performance benefit: ~10,000× speedup on angular power spectrum evaluation
Operational cost:
  - PyTorch training pipeline: ~1–2 days to build, ~4 h/month to maintain
  - Model registry: ~0.5 days to set up, ~1 h/month to maintain
  - Retraining: ~2 h per cosmological model update
Verdict: Worth it for MCMC with >50,000 steps.
         Overkill for single-shot Fisher matrix forecasting.
```
