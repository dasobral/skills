---
name: build-attack-scenario
description: Build a portable, hash-pinned agent attack scenario with explicit trusted goals, untrusted channels, prohibited effects, and benign criteria.
license: MIT
metadata:
  plugin: agent-attack-replay
  version: "0.1.0"
---

# Build Attack Scenario

Define a controlled evaluation; do not execute it while building the artifact.
Use synthetic, non-sensitive payloads and fixtures. Never place production
credentials, private prompts, personal data, or live endpoints in a scenario.

## Workflow

1. Create a definition containing the trusted goal, untrusted channel, payload
   family, prohibited side effects, benign success criteria, repetitions, and
   relative fixture paths. Add monitor-executable benign assertions and separate
   `attacker`, `victim`, and `judge` role inputs; never share hidden attacker
   reasoning with the judge.
2. Run
   `python3 scripts/build_attack_scenario.py definition.json --base-dir FIXTURES > scenario.json`.
3. Review the computed SHA-256 fixture and packaged TOML role-definition hashes.
4. Validate with
   `python3 scripts/build_attack_scenario.py --validate scenario.json`.
5. Require the replay harness's temporary workspace, mediated structured tools,
   deny-all network monitor, and hash-bound filesystem observations. An agent's
   statement that isolation or success exists is not enforcement evidence.

The generated scenario records hashes, not fixture contents. See
`references/schemas/scenario.schema.json`.
Definitions and outputs use Draft 2020-12 validation first. Missing
`jsonschema==4.26.0` yields an `evidence-gap` with setup guidance.
