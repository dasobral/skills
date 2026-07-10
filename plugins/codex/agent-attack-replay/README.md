# Agent Attack Replay

Controlled scenario construction and repeatable agent-attack evaluation with evidence-bound trial records.

## Daily workflow

1. Use `build-attack-scenario` to define the trusted goal, untrusted channel, prohibited side effects, benign criteria, repetitions, and fixture hashes.
2. Review authorization and provision an isolated executor and monitor.
3. Use `run-agent-attack-replay` to run attacker, victim, and judge roles across all trials.
4. Validate the ledger, intervals, minimized traces, and retained originals before comparing regressions.

## Triggers

Use for prompt-injection regression, tool-abuse evaluation, model/prompt/tool fixture changes, or benign-utility measurement. The hook only reports relevant replay-fixture changes.

## Required inputs

- Explicit authorization, immutable scenario, approved fixture digests, and role-template hashes.
- Isolated executor, trusted side-effect monitor, repetition count, and acceptance thresholds.
- External anchor and prior ledger state for security measurements.

## Artifacts

- Attack scenario, trial results, monitor observations, and regression summary.
- Wilson confidence intervals for attack success and benign utility.
- Hash-linked ledger, external anchor, and minimized successful traces that retain originals.

## Agent authority

The attacker and victim act only inside the authorized sandbox. The transcript judge receives no hidden attacker reasoning, cannot modify trial artifacts, and does not set acceptance policy.

## Deterministic checks and agent decisions

Fixture hashes, sandbox preflight, side-effect assertions, counts, intervals, and ledger validation are deterministic. Scenario realism, transcript interpretation, and release decisions remain reviewed judgments.

## Data guarantees

Security measurements require trusted monitor observations and immutable role/fixture identities. Scripted self-tests are labeled not-applicable and are not represented as real model evaluations.

## Limitations and non-claims

This plugin does not prove model safety, eliminate attacks, authorize testing against third parties, or generalize results beyond the pinned environment and repetitions.
