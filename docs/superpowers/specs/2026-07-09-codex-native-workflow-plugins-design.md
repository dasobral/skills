# Codex-Native Workflow Plugins Design

## Purpose

Make the repository's plugin pipeline genuinely compatible with current Codex plugin discovery, preserve Cursor output, and add evidence-producing plugins for recurring agent-security, cryptographic, QRNG, and scientific-computing work.

## Current-state assessment

The portable skills themselves are compatible with Codex's `SKILL.md` format, but the generated Codex bundles are not native Codex plugins.

The existing exporter writes:

- `.agents/skills/<skill>/`
- a custom `bundle.json`
- `AGENTS.md` containing `@.agents/instructions.md`

Current Codex plugins instead require `.codex-plugin/plugin.json`. Native plugin manifests may point to `skills/`, hooks, MCP server configuration, applications, and presentation assets. Plugin and marketplace paths must be relative, begin with `./`, and remain within their containing root.

The generated `AGENTS.md` include is also unsafe as a compatibility assumption. Codex loads hierarchical `AGENTS.md` files, but `@file` expansion is not a stable general-purpose instruction import contract. Native plugins should package workflow instructions as skills and hooks rather than rely on that include.

The six Cursor plugins additionally contain Cursor-specific agents, rules, and hooks. Codex cannot consume those files unchanged:

- Cursor Markdown agents differ from Codex project or user agent TOML.
- Cursor `.mdc` rules have no direct Codex plugin-manifest component.
- Cursor hook event names, input/output contracts, and environment variables differ.
- Native Codex plugin manifests do not currently declare custom agents.

Therefore, all six existing plugin families need generated Codex-native counterparts rather than copies of their Cursor directories.

## Design principles

1. Keep `core/skills/` as the portable source of truth.
2. Keep platform behavior in platform adapters.
3. Generate committed, inspectable native plugins for both Cursor and Codex.
4. Build plugins around recurring workflows and concrete artifacts, not occupational categories.
5. Use deterministic code for enforcement, calculation, hashing, and pass/fail decisions.
6. Use agents for interpretation, adversarial challenge, and review, never as the only security boundary.
7. Preserve provenance and distinguish verified facts, inferred findings, and evidence gaps.
8. Never imply certification, validation, or cryptographic security when the available evidence does not establish it.

## Repository architecture

### Portable core

`core/manifest.yaml` continues to define plugin families and portable skills. It gains platform-neutral metadata needed by both marketplaces and the five workflow plugin definitions.

`core/skills/` contains portable workflows, references, schemas, and deterministic helper scripts. Platform-specific commands, file locations, agent installation, and hook contracts remain outside the core.

### Codex adapters

Each native Codex plugin has an authoring overlay at:

`adapters/codex/<plugin>/`

An overlay may contain:

- `.codex-plugin/plugin.json` metadata overrides
- `hooks/hooks.json` and hook scripts
- `agents/*.toml` templates
- Codex-specific skill references
- policy or schema files needed by deterministic checks

No overlay path may be absolute or traverse outside its plugin directory.

### Generated output

The exporter writes native, committed plugins to:

`plugins/codex/<plugin>/`

Each generated plugin contains:

- `.codex-plugin/plugin.json`
- `skills/<skill>/SKILL.md`
- optional `hooks/hooks.json` and scripts
- optional `agents/*.toml` templates
- `README.md`

The repository marketplace lives at:

`.agents/plugins/marketplace.json`

Every marketplace `source.path` begins with `./`, resolves relative to the marketplace root, and points to a real plugin directory.

The existing `dist/codex` flat skill export may remain for direct skill installation, but custom `bundle.json` directories are no longer described as Codex plugins. Documentation clearly distinguishes a portable skill archive from an installable native plugin.

## Custom agent delivery

Codex discovers custom agents from `.codex/agents/*.toml` in a project or `~/.codex/agents/*.toml` for a user. Native plugin manifests do not currently expose an `agents` component.

Plugins therefore package agent TOML files as templates and include a setup skill that:

1. asks the user to choose project or user scope;
2. validates the destination is exactly `.codex/agents` or `~/.codex/agents`;
3. previews additions and collisions;
4. refuses path traversal and silent overwrite;
5. writes atomically;
6. records installed template version and content hash;
7. is idempotent when the installed template already matches.

Agent definitions contain `name`, `description`, and `developer_instructions`. Optional model, sandbox, MCP, or skill configuration is omitted unless the workflow genuinely requires it, allowing inheritance from the parent session.

## Existing plugin adaptations

The exporter generates Codex-native versions of:

1. `codecraft`
2. `cpp-qkd-toolkit`
3. `agent-platform`
4. `aos-stack`
5. `scientific-computing`
6. `career-writer`

Portable skills are reused. Cursor-specific behavior is adapted as follows:

- Cursor agents become Codex TOML templates plus a setup skill.
- Objective `.mdc` guidance becomes portable skill guidance or concise Codex policy references.
- Cursor hooks are reimplemented against Codex event names and input/output contracts.
- Hooks that merely announce context are removed when a skill description provides sufficient discovery.
- Unsupported behavior is documented rather than simulated with an unreliable prompt convention.

## New workflow plugins

### 1. `agentic-trust-gate`

**Daily problem:** A developer clones a repository, installs a plugin, enables a hook, or connects an MCP server without a concise view of the code and authority that will become trusted.

**Triggers:**

- first repository assessment;
- changes to agent instructions, skills, hooks, MCP configuration, package lifecycle scripts, editor tasks, or agent definitions;
- changes to remote MCP tool manifests or authorization scopes.

**Workflow:**

1. Inventory executable startup surfaces and agent-control files.
2. Classify each source as user-authored, repository-controlled, dependency-controlled, retrieved, or remote-mutable.
3. Diff requested capabilities against the last approved snapshot.
4. Detect hidden instructions, unpinned execution, path escape, tool-name shadowing, scope expansion, token passthrough, and mutable remote descriptors.
5. Produce one parameter-bound trust decision instead of a sequence of low-context prompts.
6. Save an approval record keyed by repository identity, revision, plugin/tool manifest hashes, and capability set.

**Artifacts:**

- `trust-inventory.json`
- `capability-delta.json`
- `trust-decision.md`
- content-hash ledger

**Agents:**

- configuration archaeologist;
- capability analyst.

Agents may classify and explain suspicious content. Deterministic policy decides objective path, hash, signature, and scope violations.

### 2. `agent-attack-replay`

**Daily problem:** Prompt-injection and tool-misuse defenses are tested once with familiar strings, while adaptive attacks, retries, indirect context, and chained side effects remain unmeasured.

**Triggers:**

- prompt, model, tool, permission, memory, retrieval, skill, or hook changes;
- production near misses;
- pre-release and scheduled security evaluation.

**Workflow:**

1. Convert incidents and threat hypotheses into versioned scenarios.
2. Mutate delivery channels across repository files, tool descriptions, RAG content, memory, URLs, and user-copied text.
3. Run repeated trials because one-shot success rates understate probabilistic risk.
4. Separate benign utility, attack success, unauthorized side effects, detection latency, and blast radius.
5. Minimize successful traces and promote them into permanent regressions.

**Artifacts:**

- scenario corpus;
- per-consequence attack-success report;
- utility/security comparison;
- minimized exploit trace;
- machine-readable regression result.

**Agents:**

- sandboxed attacker;
- victim role;
- independent transcript judge.

The judge does not share hidden attacker state. Deterministic trace assertions decide whether prohibited side effects occurred.

### 3. `crypto-change-radar`

**Daily problem:** Cryptographic changes are hidden behind wrappers, providers, protocol negotiation, certificates, build outputs, and dependency updates. Teams discover migration blockers only during audits or incidents.

**Triggers:**

- source and dependency changes;
- builds and container changes;
- certificate, provider, protocol, or policy changes;
- standards and protocol-draft updates.

**Workflow:**

1. Reconcile source, dependency, binary, configuration, certificate, and permitted runtime observations into a cryptographic bill of materials.
2. Produce a semantic PR/build delta, not a text diff.
3. Identify new quantum-vulnerable assets, provider-boundary changes, deprecated algorithms, hard-coded policy, unknown ownership, and negotiation downgrade.
4. Review hybrid constructions for component ordering, encoding, domain separation, KDF use, failure handling, and transcript binding.
5. Generate a risk-ranked PQC migration queue from confidentiality lifetime, system lifetime, updateability, dependency graph, and migration lead time.
6. Generate exact-version interoperability matrices for deployed libraries, protocols, codepoints, certificates, and fallback behavior.

**Artifacts:**

- CycloneDX cryptographic inventory;
- semantic CBOM delta;
- owner-routed findings;
- PQC migration queue;
- interoperability matrix;
- standards lock and drift report;
- release evidence index.

**Agents:**

- crypto archaeologist;
- protocol challenger;
- evidence notary.

The plugin says that evidence is consistent with a named module boundary or validation record only when exact versions and operational conditions match. It never equates algorithm support or test-vector success with FIPS validation.

### 4. `entropy-flight-recorder`

**Daily problem:** QRNG teams run statistical tests but lose the source identity, pre-conditioned samples, restart data, operating conditions, estimator versions, and rationale needed to reproduce an entropy claim or diagnose field drift.

**Triggers:**

- device, firmware, driver, conditioner, sampler, or operating-envelope changes;
- qualification runs;
- health-test parameter changes;
- continuous telemetry incidents.

**Workflow:**

1. Record the noise-source model, adversarial assumptions, digitization boundary, conditioning path, hardware and firmware identity, and claimed operating envelope.
2. Preserve authorized raw pre-conditioned datasets and restart matrices with hashes and access controls.
3. Run reproducible IID/non-IID estimation, restart analysis, and declared physics-specific failure checks.
4. Derive and record continuous health-test parameters from the claimed entropy rate and false-positive target.
5. Map source, conditioner, DRBG, reseed, and prediction-resistance paths to the applicable random-bit-generator construction.
6. Detect whether a change requires requalification.

**Artifacts:**

- `source.yaml`;
- immutable run manifest;
- estimator and restart results;
- health-test parameter record;
- operating-envelope coverage;
- RBG topology;
- requalification decision;
- evidence-gap report.

**Agents:**

- entropy analyst;
- source-physics skeptic;
- evidence curator.

Raw production random output is not logged. Statistical output quality alone is never presented as proof of quantum origin, min-entropy, or compliance.

### 5. `scientific-claim-ledger`

**Daily problem:** Simulation and scientific-ML results are detached from their context of use, units, environment, numerical error, uncertainty, validation data, and acceptance threshold, making plausible but unsupported claims difficult to detect.

**Triggers:**

- simulation or training runs;
- changes to equations, numerical kernels, units, data splits, solvers, surrogates, or acceptance criteria;
- merge, publication, and release preparation.

**Workflow:**

1. Declare the quantity of interest, context of use, units, tolerances, uncertainty meaning, and acceptance threshold before execution.
2. Capture source revision, inputs, dependencies, compiler/runtime configuration, hardware, parallel layout, seeds, and exact replay command.
3. Separate code verification, solution verification, model validation, and uncertainty quantification.
4. Reject performance comparisons when scientific correctness has not passed.
5. Challenge surrogates and physics-informed ML for leakage, residual/error mismatch, extrapolation, conservation or invariance failures, weak baselines, seed sensitivity, and uncalibrated uncertainty.
6. Link every published claim to tests, runs, artifacts, and reviewer decisions.

**Artifacts:**

- immutable run record;
- unit and coordinate-frame registry;
- convergence and numerical-equivalence results;
- uncertainty and sensitivity report;
- surrogate/SciML challenge report;
- claim-to-evidence graph;
- reproducible research package index.

**Agents:**

- numerical verifier;
- SciML challenger;
- claim auditor.

The agent assessing a claim cannot modify the run artifacts or acceptance criteria it reviews.

## Hook policy

Hooks remain deterministic, fast, and narrowly scoped.

They may block:

- invalid manifests or paths;
- changed executable or remote tool definitions lacking review;
- objective policy violations;
- missing required provenance fields;
- cryptographic primitives explicitly forbidden by the selected policy;
- missing raw-source identity in an entropy qualification run;
- incompatible units, non-finite values, solver non-convergence, or failed declared invariants;
- use of validation data for calibration when the run contract prohibits it.

They may warn or request review for:

- suspected prompt injection;
- model adequacy;
- physical-source plausibility;
- choice of prior or uncertainty model;
- extrapolation risk;
- compliance interpretation.

Every hook documents its event, expected input, output contract, trust requirement, timeout behavior, and failure mode. Security-critical checks fail closed. Optional evidence collectors produce an explicit incomplete-evidence state rather than an implicit pass.

## Evidence and data handling

Workflow artifacts live under a configurable project evidence directory with versioned JSON schemas.

Every material finding records:

- originating source and retrieval or observation time;
- tool and ruleset version;
- command or deterministic procedure;
- confidence and evidence classification;
- input and output artifact hashes;
- reviewer or policy decision;
- standards revision when applicable.

The default collectors never capture:

- private keys or session secrets;
- QKD or QRNG production key material;
- credentials or bearer tokens;
- production payload contents;
- sensitive simulation datasets not explicitly selected by the user.

Evidence schemas distinguish `pass`, `fail`, `unknown`, `not-applicable`, and `evidence-gap`. Missing optional tools cannot produce `pass`.

## Validation and testing

### Static validation

- Parse every `.codex-plugin/plugin.json`.
- Require lowercase kebab-case names and coherent metadata.
- Require component paths to start with `./`, remain relative, stay inside the plugin, and resolve to existing files.
- Validate marketplace uniqueness and source paths.
- Validate skill frontmatter and supported field lengths.
- Parse every agent TOML and require `name`, `description`, and `developer_instructions`.
- Parse hook JSON and validate referenced commands and scripts.
- Reject absolute paths, parent traversal, broken references, and undeclared generated files.

### Export tests

Golden and structural tests cover all eleven Codex plugins and all six Cursor plugins. Tests prove:

- portable skills are copied without loss;
- Codex overlays do not leak into Cursor output;
- Cursor overlays do not leak into Codex output;
- clean exports remove stale generated files;
- deterministic exports are byte-identical for unchanged inputs;
- marketplace generation remains synchronized with the manifest.

### Codex compatibility tests

When the Codex CLI and its marketplace subcommands are available, integration
tests use an isolated home and repository to add and inspect the local
marketplace. Current official CLI commands manage marketplace sources; local
plugin installation is completed through the ChatGPT desktop plugin directory.

The same isolated test validates generated plugin manifests, skills, hooks, and
project-scoped agent installation locally. It does not present those local
checks as proof that the CLI loaded or installed plugin components. Tests avoid
altering the developer's real Codex configuration.

### Agent installer tests

Temporary-home tests cover:

- project and user destinations;
- idempotent reinstall;
- identical and conflicting existing files;
- atomic writes;
- interrupted installation;
- path traversal and symlink escape;
- install record and hash accuracy.

### Workflow scenarios

Fixtures cover:

- malicious repository instructions and executable startup configuration;
- MCP schema drift, tool shadowing, and scope expansion;
- repeated indirect prompt injection with prohibited side-effect assertions;
- semantic cryptographic inventory changes and hybrid-construction mistakes;
- incomplete QRNG source records, changed conditioning, and requalification triggers;
- unit mismatch, numerical non-convergence, data leakage, and unsupported SciML claims.

## Documentation

The root README explains:

- native Cursor and Codex plugin locations;
- portable flat-skill exports;
- marketplace installation;
- hook trust review;
- custom agent template installation;
- generated-versus-authored directories;
- how to add a portable skill or platform adapter.

Each plugin README states:

- the daily workflow it solves;
- triggers, required inputs, and generated artifacts;
- installed agents and their authority;
- deterministic checks versus agent judgment;
- data-handling guarantees;
- limitations and non-claims.

## Research basis

The workflow designs are grounded in:

- OpenAI Codex documentation for plugins, skills, hooks, marketplaces, `AGENTS.md`, and custom agents;
- OWASP Top 10 for Agentic Applications 2026 and OWASP MCP security guidance;
- MITRE ATLAS and SAFE-AI;
- NIST CAISI agent-hijacking evaluation guidance;
- AgentDojo and adaptive agent-security evaluation research;
- NIST SP 800-90B and SP 800-90C;
- NIST IR 8446 and BSI AIS 20/31;
- FIPS 203, 204, and 205;
- NIST cryptographic-agility and PQC migration guidance;
- CycloneDX cryptographic-asset modeling;
- ETSI QKD application-interface guidance;
- NASA-STD-7009B, ASME V&V/VVUQ guidance, and JCGM uncertainty guidance;
- current scientific-ML verification, PINN failure-mode, leakage, and baseline-quality research.

Normative references used by deterministic checks are version-pinned in repository reference data. A scheduled standards-drift workflow reports changes but does not silently rewrite policy.

## Non-goals

- Providing legal, certification-lab, or accreditation decisions.
- Claiming that statistical tests prove quantum origin or entropy security.
- Inventing cryptographic constructions or protocol combiners.
- Treating QKD as a replacement for authentication, endpoint security, key management, or PQC migration.
- Treating an LLM classifier or reviewer as a security enforcement boundary.
- Automatically trusting plugin hooks or installing user-scoped agents without an explicit choice.
- Adding external MCP services or authentication dependencies in this phase.
