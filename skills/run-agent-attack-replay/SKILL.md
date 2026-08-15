---
name: run-agent-attack-replay
description: Aggregate isolated agent attack trials with deterministic side-effect assertions, Wilson intervals, and preserved trace evidence.
license: MIT
metadata:
  plugin: agent-attack-replay
  version: "0.1.0"
---

# Run Agent Attack Replay

Run attacker, victim, and judge as pluggable executor subprocesses over
`agent-executor-rpc-v1`. Executors receive only role-scoped inputs and use
line-delimited structured tool RPC; the parent alone touches the replay workspace,
mediates network/filesystem effects, and records observations.

## Workflow

1. Provide an executor config with an argv array for each packaged TOML role.
   Include an approved absolute input root and digest-bound manifest for every
   absolute argument. Undeclared, out-of-root, changed, or duplicate inputs are
   refused before execution.
   Caller-declared side effects, success, evidence states, and judge outcomes are
   rejected. Plan `role_actions` are used only by explicit harness self-test mode.
   Security measurement requires fixed `/usr/bin/bwrap`, or an explicitly
   configured root-owned executable on a non-writable path. Inherited `PATH`
   and current-user wrappers are never trusted; no direct host fallback exists.
2. Give the attacker only synthetic attack material, the victim only its trusted
   goal and modeled channel, and the judge only hashed visible tool transcript and
   monitor evidence. Never give the judge hidden attacker reasoning.
3. Keep secrets, chain-of-thought, credentials, raw tool results, and private data
   out of the plan and output. Requests/results appear only as hashes.
4. Set `PLUGIN_DATA` or pass `--state-dir`. Run
   `python3 scripts/run_agent_attack_replay.py scenario.json replay-plan.json --fixtures-dir FIXTURES --executor-config executors.json --state-dir STATE --anchor-out replay-anchor.json > regression-summary.json`.
5. The state directory holds a mode-`0600` HMAC key, locked append-only trust
   ledger, and create-only anchor. Never copy the key into a scenario, summary,
   executor envelope, or anchor.
6. Validate every schema and calculation plus authenticated envelopes,
   observations, role templates, scenario, summary, and ledger chain with
   `python3 scripts/run_agent_attack_replay.py --validate regression-summary.json --state-dir STATE --anchor replay-anchor.json`.
7. `--self-test-scripted-workers` tests harness plumbing only. It reports
   `not-applicable` and `review-required`, never security pass/allow. Without an
   executor config or explicit self-test mode, the command returns `evidence-gap`.
   Missing/untrusted Bubblewrap or invalid input manifests likewise return
   `evidence-gap` and run no executor.
8. Bubblewrap unshares network, PID, IPC, UTS, cgroup, and mount namespaces. It
   exposes only per-role `/request` and `/work`, `/proc`, `/dev`, `/tmp`, the
   executor binary, and minimal runtime library directories—never `/home`,
   `/workspace`, the project tree, or the full host root.
9. Treat monitor-generated prohibited-side-effect assertions as authoritative.
   The deterministic judge projection is supporting review evidence only.
10. Retain each complete hashed tool transcript. The generated minimized trace is an additional
   prefix ending at the first objective violation and never replaces the original.

The script requires `jsonschema==4.26.0`; absence produces an `evidence-gap`
with setup guidance, never a traceback.
