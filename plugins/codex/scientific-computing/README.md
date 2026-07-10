# Scientific Computing

Architecture guidance for right-sized scientific computing platforms and separated compute layers.

## Daily workflow

1. Use `scientific-platform-architect` to define the scientific workloads and quantities of interest.
2. Separate interactive, orchestration, simulation, training, and serving concerns.
3. Compare infrastructure options against measured scale and operational constraints.
4. Record decisions, assumptions, rejected alternatives, and validation work.

## Triggers

Use for HPC and cloud architecture, emulator platforms, PyTorch workloads, storage/dataflow design, or infrastructure-sizing decisions.

## Required inputs

- Scientific use cases, workload shapes, data sizes, and software stack.
- Accuracy, latency, throughput, reproducibility, security, and budget constraints.
- Existing infrastructure, measured bottlenecks, and deployment boundaries.

## Artifacts

- Platform architecture and compute-layer map.
- Capacity assumptions, option comparison, and staged implementation plan.
- Risks, benchmarks to run, and decision records.

## Agent authority

The platform designer may propose and critique architectures. It cannot purchase resources, approve scientific adequacy, change budgets, or install its template automatically.

## Deterministic checks and agent decisions

Inventory, benchmark results, compatibility checks, and cost inputs are deterministic evidence when versioned. Sizing, trade-offs, architecture selection, and risk tolerance remain reviewed decisions.

## Data guarantees

Artifacts must separate measured facts from estimates and identify source revisions. No hook runs and no infrastructure is modified by this plugin.

## Limitations and non-claims

This plugin does not guarantee scientific validity, benchmark portability, cost forecasts, scalability, uptime, or regulatory compliance.
