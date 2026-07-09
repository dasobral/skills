# Codex-Native Workflow Plugins Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate, validate, test, and document six adapted and five new native Codex plugins while preserving the existing Cursor and flat-skill pipelines.

**Architecture:** Portable skills and plugin metadata remain in `core/`; Codex-only manifests, hooks, agent templates, schemas, and setup behavior live in `adapters/codex/`. The exporter combines both layers into committed `plugins/codex/` output and a native `.agents/plugins/marketplace.json`; deterministic validators and scenario tests prove path safety, reproducibility, and evidence semantics.

**Tech Stack:** Python 3.10+, PyYAML, pytest, JSON Schema-compatible JSON fixtures, TOML via Python `tomllib`, shell launchers, Codex native plugin/marketplace formats.

---

## File structure

### Export framework

- Modify `core/manifest.yaml`: register Codex support and five workflow plugin families.
- Modify `landing/registry.yaml`: map newly ingested workflow skills to their plugin families.
- Modify `tools/skills-export/skills_export/manifest.py`: expose Codex adapter and generated-plugin roots.
- Replace native-plugin portions of `tools/skills-export/skills_export/exporters/codex.py`: generate native plugins and marketplace while retaining flat skill export.
- Create `tools/skills-export/skills_export/validate_codex.py`: validate manifests, paths, skills, hooks, agents, and marketplace entries.
- Create `tools/skills-export/skills_export/agent_installer.py`: safely install bundled TOML agent templates.
- Modify `tools/skills-export/skills_export/cli.py`: add `sync codex` and Codex validation.
- Modify `tools/skills-export/skills_export/maintain.py`: sync committed Codex plugins and export flat skills.
- Modify `bin/skills-install`: install Codex plugins or flat skills explicitly.

### Authoring overlays

- Replace `adapters/codex/README.md`: explain authored overlays and generated output.
- Create `adapters/codex/<existing-plugin>/` for all six existing plugins.
- Create `adapters/codex/<workflow-plugin>/` for all five workflow plugins.
- Create `adapters/codex/_shared/skills/install-plugin-agents/`: reusable, generated setup skill.

### Portable workflow content

- Create `core/skills/assess-repository-trust/`.
- Create `core/skills/review-mcp-drift/`.
- Create `core/skills/build-attack-scenario/`.
- Create `core/skills/run-agent-attack-replay/`.
- Create `core/skills/build-crypto-inventory/`.
- Create `core/skills/review-crypto-delta/`.
- Create `core/skills/plan-pqc-migration/`.
- Create `core/skills/test-crypto-interoperability/`.
- Create `core/skills/qualify-entropy-source/`.
- Create `core/skills/review-entropy-change/`.
- Create `core/skills/capture-scientific-run/`.
- Create `core/skills/audit-scientific-claim/`.
- Create `core/skills/challenge-sciml-model/`.

Each skill owns its workflow instructions and references. Deterministic artifact contracts live in `core/skills/<skill>/references/` rather than in one cross-domain schema module.

### Tests

- Modify `tools/skills-export/pyproject.toml`: add pytest test extras and configuration.
- Create `tools/skills-export/tests/conftest.py`.
- Create `tools/skills-export/tests/test_codex_export.py`.
- Create `tools/skills-export/tests/test_codex_validation.py`.
- Create `tools/skills-export/tests/test_agent_installer.py`.
- Create `tools/skills-export/tests/test_workflow_contracts.py`.
- Create `tools/skills-export/tests/test_cursor_regression.py`.
- Create `tools/skills-export/tests/integration/test_codex_cli.py`.
- Create `tools/skills-export/tests/fixtures/` for invalid plugins and workflow scenarios.

## Task 1: Establish executable tests and native layout expectations

**Files:**
- Modify: `tools/skills-export/pyproject.toml`
- Create: `tools/skills-export/tests/conftest.py`
- Create: `tools/skills-export/tests/test_codex_export.py`
- Create: `tools/skills-export/tests/test_cursor_regression.py`

- [ ] **Step 1: Add the test dependency and markers**

Add:

```toml
[project.optional-dependencies]
test = ["pytest"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
  "integration: requires an installed Codex CLI",
]
```

- [ ] **Step 2: Write a repository-copy fixture**

`conftest.py` must expose `repo_copy(tmp_path)` that copies only `core/`, `adapters/`, `.cursor-plugin/`, and tool source into a temporary root. Tests must never regenerate the working tree directly.

- [ ] **Step 3: Write failing native export tests**

Assert that a native export of `codecraft` creates:

```text
plugins/codex/codecraft/.codex-plugin/plugin.json
plugins/codex/codecraft/skills/analyze-codebase/SKILL.md
plugins/codex/codecraft/agents/code-reviewer.toml
plugins/codex/codecraft/skills/install-plugin-agents/SKILL.md
```

Assert that the manifest contains:

```json
{
  "name": "codecraft",
  "skills": "./skills/",
  "hooks": "./hooks/hooks.json"
}
```

Assert all component paths begin with `./`.

- [ ] **Step 4: Write a failing Cursor isolation test**

Hash every file under generated `plugins/cursor/`, invoke Codex native export in the temporary repository, and assert the hashes remain unchanged.

- [ ] **Step 5: Run tests to verify failure**

Run: `python -m pytest tools/skills-export/tests/test_codex_export.py tools/skills-export/tests/test_cursor_regression.py -v`

Expected: FAIL because native Codex export and adapters do not exist.

- [ ] **Step 6: Commit the test foundation**

```bash
git add tools/skills-export/pyproject.toml tools/skills-export/tests
git commit -m "test: define native Codex plugin expectations"
```

## Task 2: Add Codex manifest helpers and plugin metadata

**Files:**
- Modify: `tools/skills-export/skills_export/manifest.py`
- Modify: `core/manifest.yaml`
- Modify: `landing/registry.yaml`
- Test: `tools/skills-export/tests/test_codex_export.py`

- [ ] **Step 1: Add failing helper tests**

Assert:

```python
assert codex_adapter_dir(root, "codecraft") == root / "adapters/codex/codecraft"
assert codex_plugins_dir(root) == root / "plugins/codex"
```

- [ ] **Step 2: Implement path helpers**

Add:

```python
def codex_adapter_dir(root: Path, plugin_name: str) -> Path:
    return root / "adapters" / "codex" / plugin_name


def codex_plugins_dir(root: Path) -> Path:
    return root / "plugins" / "codex"
```

- [ ] **Step 3: Register the workflow plugins**

Add these exact plugin-to-skill mappings to `core/manifest.yaml`:

```yaml
agentic-trust-gate:
  skills: [assess-repository-trust, review-mcp-drift]
agent-attack-replay:
  skills: [build-attack-scenario, run-agent-attack-replay]
crypto-change-radar:
  skills: [build-crypto-inventory, review-crypto-delta, plan-pqc-migration, test-crypto-interoperability]
entropy-flight-recorder:
  skills: [qualify-entropy-source, review-entropy-change]
scientific-claim-ledger:
  skills: [capture-scientific-run, audit-scientific-claim, challenge-sciml-model]
```

Give each a display name, version `0.1.0`, focused description, category, keywords, tags, and `codex` metadata declaring agents and hooks. Add `codex` metadata to the six existing plugin records.

- [ ] **Step 4: Update landing assignments**

Map all thirteen skill names to their plugin names in `landing/registry.yaml`; do not create alternate plugin records there.

- [ ] **Step 5: Run helper and core validation tests**

Run: `python -m pytest tools/skills-export/tests/test_codex_export.py -v`

Expected: helper assertions PASS; export assertions still FAIL.

Run: `./bin/skills-export validate`

Expected: FAIL listing the thirteen missing core skill directories. This verifies the manifest is enforcing completeness.

- [ ] **Step 6: Commit manifest modeling**

```bash
git add core/manifest.yaml landing/registry.yaml tools/skills-export/skills_export/manifest.py tools/skills-export/tests/test_codex_export.py
git commit -m "feat: model Codex plugin families"
```

## Task 3: Implement the native Codex exporter and marketplace

**Files:**
- Modify: `tools/skills-export/skills_export/exporters/codex.py`
- Create: `.agents/plugins/marketplace.json` through generation
- Test: `tools/skills-export/tests/test_codex_export.py`

- [ ] **Step 1: Expand failing tests**

Cover:

- all manifest plugins exported under `plugins/codex/`;
- clean export removes stale files;
- two unchanged exports are byte-identical;
- marketplace has eleven unique entries;
- every `source.path` is `./plugins/codex/<name>`;
- flat export still writes `dist/codex/skills/`;
- legacy `bundle.json` and `AGENTS.md` are absent.

- [ ] **Step 2: Implement manifest assembly**

Create `_assemble_plugin_json(plugin_name, plugin_meta, overlay)` that:

1. starts with `name`, `version`, `description`, author, license, keywords;
2. adds `"skills": "./skills/"`;
3. adds `"hooks": "./hooks/hooks.json"` only when that file is copied;
4. merges safe presentation fields from the overlay;
5. rejects component paths without `./`.

- [ ] **Step 3: Implement one-plugin export**

`export_codex_plugin(root, plugin_name, output_root, clean=True)` must:

1. write to `output_root/<plugin_name>`;
2. copy mapped core skills to `skills/`;
3. merge adapter-local `skills/`;
4. copy `hooks/`, `agents/`, and safe assets from the adapter;
5. inject the shared `install-plugin-agents` skill when agents exist;
6. write `.codex-plugin/plugin.json`;
7. write a generated README listing skills, agents, hooks, and data-handling notes.

- [ ] **Step 4: Implement marketplace generation**

Write `.agents/plugins/marketplace.json` with:

```json
{
  "name": "dasobral-skills",
  "interface": {"displayName": "Dasobral Skills"},
  "plugins": [
    {
      "name": "codecraft",
      "source": {"path": "./plugins/codex/codecraft"},
      "interface": {"displayName": "Codecraft"}
    }
  ]
}
```

Generate entries in manifest order and use stable JSON formatting.

- [ ] **Step 5: Preserve flat export**

Keep `export_codex_flat`, but remove native-bundle generation. `export_codex()` must accept distinct native and flat destinations so `sync codex` and `export codex` cannot overwrite each other.

- [ ] **Step 6: Run exporter tests**

Run: `python -m pytest tools/skills-export/tests/test_codex_export.py tools/skills-export/tests/test_cursor_regression.py -v`

Expected: failures only for missing adapters and skills, not exporter layout.

- [ ] **Step 7: Commit exporter**

```bash
git add tools/skills-export/skills_export/exporters/codex.py tools/skills-export/tests
git commit -m "feat: generate native Codex plugins"
```

## Task 4: Add static Codex validation

**Files:**
- Create: `tools/skills-export/skills_export/validate_codex.py`
- Create: `tools/skills-export/tests/test_codex_validation.py`
- Create: `tools/skills-export/tests/fixtures/invalid-codex-plugins/`

- [ ] **Step 1: Write failing validator cases**

Fixtures must cover:

- missing `.codex-plugin/plugin.json`;
- invalid JSON;
- non-kebab-case name;
- absolute component path;
- path without `./`;
- `../` traversal;
- symlink escape;
- missing referenced directory;
- missing skill frontmatter;
- invalid agent TOML;
- missing agent required keys;
- hook command referencing a missing script;
- duplicate marketplace plugin;
- marketplace source outside repository root.

- [ ] **Step 2: Implement result types**

Use:

```python
@dataclass(frozen=True)
class ValidationIssue:
    path: Path
    message: str


def validate_codex_plugins(root: Path) -> list[ValidationIssue]:
    ...
```

Sort issues by normalized relative path and message for deterministic output.

- [ ] **Step 3: Implement containment checks**

Resolve each declared path and require:

```python
raw.startswith("./")
not Path(raw).is_absolute()
".." not in Path(raw).parts
resolved.is_relative_to(plugin_root.resolve())
```

Apply the same containment rule to marketplace sources and hook script references.

- [ ] **Step 4: Parse agents and hooks**

Use `tomllib` for agents and require non-empty `name`, `description`, and `developer_instructions`. Validate hook JSON shape and `${PLUGIN_ROOT}` command paths without executing commands.

- [ ] **Step 5: Run validator tests**

Run: `python -m pytest tools/skills-export/tests/test_codex_validation.py -v`

Expected: PASS for all malicious and valid fixtures.

- [ ] **Step 6: Commit validation**

```bash
git add tools/skills-export/skills_export/validate_codex.py tools/skills-export/tests
git commit -m "feat: validate native Codex plugins"
```

## Task 5: Add safe agent-template installation

**Files:**
- Create: `tools/skills-export/skills_export/agent_installer.py`
- Create: `adapters/codex/_shared/skills/install-plugin-agents/SKILL.md`
- Create: `adapters/codex/_shared/skills/install-plugin-agents/scripts/install_agents.py`
- Create: `tools/skills-export/tests/test_agent_installer.py`

- [ ] **Step 1: Write failing installer tests**

Test project and user scopes, dry-run preview, identical reinstall, conflicting file refusal, atomic replacement, invalid source TOML, `..` rejection, destination symlink escape, and hash-ledger output.

- [ ] **Step 2: Implement the installer API**

Expose:

```python
def install_agent_templates(
    source_dir: Path,
    *,
    scope: Literal["project", "user"],
    project_root: Path | None = None,
    home: Path | None = None,
    dry_run: bool = False,
) -> InstallResult:
    ...
```

Project destination is exactly `<project_root>/.codex/agents`; user destination is exactly `<home>/.codex/agents`. Reject symlinked destination parents escaping those roots.

- [ ] **Step 3: Implement collision and atomic-write semantics**

- matching hash: report `unchanged`;
- missing target: write a sibling temporary file, `fsync`, then `os.replace`;
- different target: report `conflict` and write nothing;
- invalid source: abort the complete batch before any write.

Write `.plugin-agent-install.json` only after all templates succeed. Include plugin name, version, relative file, and SHA-256.

- [ ] **Step 4: Add the setup skill**

The skill must instruct Codex to:

1. ask project or user scope;
2. run `install_agents.py --dry-run`;
3. show additions and conflicts;
4. obtain explicit confirmation;
5. rerun without `--dry-run`;
6. tell the user to start a new Codex session.

- [ ] **Step 5: Run installer tests**

Run: `python -m pytest tools/skills-export/tests/test_agent_installer.py -v`

Expected: PASS.

- [ ] **Step 6: Commit agent delivery**

```bash
git add tools/skills-export/skills_export/agent_installer.py adapters/codex/_shared tools/skills-export/tests/test_agent_installer.py
git commit -m "feat: install Codex agent templates safely"
```

## Task 6: Adapt the six existing plugins

**Files:**
- Create: `adapters/codex/codecraft/`
- Create: `adapters/codex/cpp-qkd-toolkit/`
- Create: `adapters/codex/agent-platform/`
- Create: `adapters/codex/aos-stack/`
- Create: `adapters/codex/scientific-computing/`
- Create: `adapters/codex/career-writer/`
- Modify: `core/skills/create-agent/SKILL.md`
- Modify: `core/skills/create-agent/references/agent-conventions.md`
- Test: `tools/skills-export/tests/test_codex_export.py`

- [ ] **Step 1: Add expected-agent tests**

Assert the converted agent counts are `2, 2, 4, 2, 1, 1`, and every TOML file has required fields. Assert no `model = "fast"`, Cursor `Task` tool, or `subagent_type` remains in Codex agent instructions.

- [ ] **Step 2: Convert the twelve agents**

For each Cursor Markdown agent, preserve its purpose and workflow in TOML:

```toml
name = "code-reviewer"
description = "Reviews implementation changes for correctness, security, tests, and repository conventions."
developer_instructions = """
Review independently. Read the applicable repository instructions and diff.
Separate blocking defects from non-blocking improvements. Cite concrete evidence.
Do not modify files unless the parent task explicitly delegates remediation.
"""
```

Use equivalent focused instructions for each role; do not hard-code a model or sandbox.

- [ ] **Step 3: Port useful hooks**

Port only:

- codecraft convention-file freshness at `SessionStart`;
- C++ cryptographic-risk hint on relevant file/tool events supported by Codex;
- AOS GPU capability context at `SessionStart`.

Drop agent-list announcement hooks because installed custom agents are discoverable. Each hook uses `${PLUGIN_ROOT}`, has a bounded timeout, emits valid Codex hook output, and never writes project files.

- [ ] **Step 4: Adapt rules**

Move objective codecraft and C++ guidance into the corresponding portable skill references. Keep Cursor `.mdc` files unchanged and generated Cursor output byte-stable.

- [ ] **Step 5: Make `create-agent` platform-aware**

Replace Cursor-only language with a platform decision:

- Cursor: Markdown agent definition;
- Codex: `.codex/agents/<name>.toml`;
- unknown platform: ask which target.

Add Codex TOML examples and required keys to `agent-conventions.md`.

- [ ] **Step 6: Run existing-plugin export and regression tests**

Run: `python -m pytest tools/skills-export/tests/test_codex_export.py tools/skills-export/tests/test_cursor_regression.py -v`

Expected: six existing Codex plugin cases PASS; workflow plugin cases remain incomplete.

- [ ] **Step 7: Commit adaptations**

```bash
git add adapters/codex core/skills/create-agent tools/skills-export/tests
git commit -m "feat: adapt existing plugins for Codex"
```

## Task 7: Implement agent-security workflow plugins

**Files:**
- Create: `core/skills/assess-repository-trust/`
- Create: `core/skills/review-mcp-drift/`
- Create: `core/skills/build-attack-scenario/`
- Create: `core/skills/run-agent-attack-replay/`
- Create: `adapters/codex/agentic-trust-gate/`
- Create: `adapters/codex/agent-attack-replay/`
- Create: `tools/skills-export/tests/test_workflow_contracts.py`
- Create: `tools/skills-export/tests/fixtures/workflows/agent-security/`

- [ ] **Step 1: Write failing contract tests**

Require schemas/examples for trust inventory, capability delta, scenario, trial result, and regression summary. Assert status enums distinguish `pass`, `fail`, `unknown`, `not-applicable`, and `evidence-gap`.

- [ ] **Step 2: Implement trust workflows**

`assess-repository-trust` inventories agent instructions, hooks, skills, MCP config, lifecycle scripts, editor tasks, devcontainers, symlinks, and executables. Its output contract requires repository identity, revision, source class, requested capability, content hash, and disposition.

`review-mcp-drift` compares canonicalized tool names, schemas, descriptions, auth endpoints, package identity, scopes, and prior hashes. It must explicitly test shadowed names, scope expansion, hidden instructions, token passthrough, and remote mutability.

- [ ] **Step 3: Implement replay workflows**

`build-attack-scenario` defines trusted goal, untrusted channel, attack payload family, prohibited side effects, benign success criteria, repetitions, and fixture hashes.

`run-agent-attack-replay` runs isolated attacker, victim, and judge roles; records every trial; uses deterministic side-effect assertions; reports Wilson confidence intervals for attack success and benign utility; and minimizes successful traces without deleting the original.

- [ ] **Step 4: Add agent templates**

Create TOML templates for:

- configuration archaeologist;
- capability analyst;
- sandboxed attacker;
- victim role;
- transcript judge.

The judge must not receive hidden attacker reasoning and must not modify trial artifacts.

- [ ] **Step 5: Add narrow hooks**

Trust-gate hooks report changed control-plane file hashes at session start. Attack-replay hooks only remind on relevant prompt/model/tool fixture changes; they do not run expensive evaluations during ordinary edits.

- [ ] **Step 6: Run workflow tests**

Run: `python -m pytest tools/skills-export/tests/test_workflow_contracts.py -k "trust or attack" -v`

Expected: PASS.

- [ ] **Step 7: Commit agent-security plugins**

```bash
git add core/skills adapters/codex/agentic-trust-gate adapters/codex/agent-attack-replay tools/skills-export/tests
git commit -m "feat: add agent security workflow plugins"
```

## Task 8: Implement cryptographic and QRNG workflow plugins

**Files:**
- Create: `core/skills/build-crypto-inventory/`
- Create: `core/skills/review-crypto-delta/`
- Create: `core/skills/plan-pqc-migration/`
- Create: `core/skills/test-crypto-interoperability/`
- Create: `core/skills/qualify-entropy-source/`
- Create: `core/skills/review-entropy-change/`
- Create: `adapters/codex/crypto-change-radar/`
- Create: `adapters/codex/entropy-flight-recorder/`
- Create: `tools/skills-export/tests/fixtures/workflows/crypto/`
- Create: `tools/skills-export/tests/fixtures/workflows/entropy/`
- Test: `tools/skills-export/tests/test_workflow_contracts.py`

- [ ] **Step 1: Write failing crypto and entropy contract tests**

Validate fixture outputs for CBOM delta, PQC queue, interoperability case, entropy source identity, qualification run, health-test parameters, and requalification decision.

- [ ] **Step 2: Implement cryptographic workflows**

The inventory workflow reconciles source, dependency, binary, configuration, certificate, and explicitly authorized runtime observations without collecting secrets.

The delta workflow reports semantic changes to algorithm, parameters, mode, protocol, provider boundary, key purpose, fallback, owner, confidence, and evidence hash.

The PQC workflow ranks assets using confidentiality lifetime, system lifetime, updateability, exposure, migration lead time, and dependencies. It uses pinned FIPS 203/204/205 and current policy references.

The interoperability workflow records exact implementation versions, protocol/draft revision, codepoint/OID, expected fallback, negotiated result, sizes, latency, fragmentation, negative tests, and reproduction command.

- [ ] **Step 3: Implement entropy workflows**

The qualification contract requires source physics, adversarial assumptions, raw sampling point, digitization, conditioning, hardware/firmware identity, claimed min-entropy, operating envelope, restart matrix identity, estimator versions, and artifact hashes.

The change-review workflow emits `requalification-required`, `review-required`, or `no-material-change` with reasons. Any hardware, firmware, conditioner, sampling-rate, driver, or operating-envelope change requires requalification unless an explicit version-pinned policy says otherwise.

- [ ] **Step 4: Add agents**

Create crypto archaeologist, protocol challenger, evidence notary, entropy analyst, source-physics skeptic, and evidence curator TOML templates. Every role must state that it cannot certify FIPS status, quantum origin, or entropy adequacy.

- [ ] **Step 5: Add objective hooks**

Crypto hooks detect changed inventory inputs and explicitly forbidden primitives selected by a checked-in policy. Entropy hooks detect qualification inputs missing source identity or changed source-boundary fields. Optional unavailable tools yield `evidence-gap`.

- [ ] **Step 6: Run workflow tests**

Run: `python -m pytest tools/skills-export/tests/test_workflow_contracts.py -k "crypto or entropy" -v`

Expected: PASS.

- [ ] **Step 7: Commit crypto and entropy plugins**

```bash
git add core/skills adapters/codex/crypto-change-radar adapters/codex/entropy-flight-recorder tools/skills-export/tests
git commit -m "feat: add crypto and entropy evidence plugins"
```

## Task 9: Implement the scientific claim workflow plugin

**Files:**
- Create: `core/skills/capture-scientific-run/`
- Create: `core/skills/audit-scientific-claim/`
- Create: `core/skills/challenge-sciml-model/`
- Create: `adapters/codex/scientific-claim-ledger/`
- Create: `tools/skills-export/tests/fixtures/workflows/science/`
- Test: `tools/skills-export/tests/test_workflow_contracts.py`

- [ ] **Step 1: Write failing scientific contract tests**

Require a run record, unit registry, numerical-equivalence result, uncertainty statement, SciML challenge result, and claim-to-evidence graph.

- [ ] **Step 2: Implement run capture**

`capture-scientific-run` requires context of use, quantity of interest, units, coordinate frame, tolerances, uncertainty meaning, acceptance threshold, source revision, input hashes, environment, compiler/runtime settings, hardware, parallel layout, seeds, and replay command.

It must classify reproducibility as `bitwise`, `numerically-equivalent`, or `scientifically-equivalent`.

- [ ] **Step 3: Implement claim audit**

`audit-scientific-claim` keeps code verification, solution verification, model validation, and UQ separate. Every claim edge must identify the test, run, artifact hash, acceptance criterion, and reviewer decision.

- [ ] **Step 4: Implement SciML challenge**

`challenge-sciml-model` checks grouped/regime-aware splits, preprocessing leakage, extrapolation, conservation, invariance, positivity, boundary conditions, residual-versus-solution error, uncertainty coverage/sharpness, seed sensitivity, strong baselines at matched error, and total cost.

- [ ] **Step 5: Add agents and hooks**

Create numerical verifier, SciML challenger, and claim auditor agents. Hooks block only objective missing provenance, invalid units, non-finite results, declared invariant failure, or forbidden calibration/validation overlap. Model adequacy remains a review finding.

- [ ] **Step 6: Run workflow tests**

Run: `python -m pytest tools/skills-export/tests/test_workflow_contracts.py -k science -v`

Expected: PASS.

- [ ] **Step 7: Commit scientific plugin**

```bash
git add core/skills adapters/codex/scientific-claim-ledger tools/skills-export/tests
git commit -m "feat: add scientific claim ledger plugin"
```

## Task 10: Wire CLI, maintenance, installation, and generated output

**Files:**
- Modify: `tools/skills-export/skills_export/cli.py`
- Modify: `tools/skills-export/skills_export/maintain.py`
- Modify: `bin/skills-install`
- Regenerate: `plugins/codex/`
- Regenerate: `.agents/plugins/marketplace.json`
- Test: `tools/skills-export/tests/test_codex_export.py`

- [ ] **Step 1: Add failing CLI tests**

Assert:

- `sync codex` writes committed native output;
- `export codex` writes flat skills only;
- `validate codex` validates generated output;
- `maintain --dry-run` reports both Cursor and Codex sync targets;
- installer requires explicit `--plugins` for native plugin installation.

- [ ] **Step 2: Add CLI routing**

Support:

```text
skills-export sync cursor
skills-export sync codex
skills-export validate
skills-export validate codex
skills-export export codex
```

The default `validate` runs core and both generated-platform checks when generated trees exist.

- [ ] **Step 3: Update maintenance**

The maintain sequence becomes:

```text
ingest -> validate core -> sync cursor -> sync codex -> validate generated plugins -> export flat Claude/Codex skills
```

Dry-run must perform no filesystem writes.

- [ ] **Step 4: Update installer**

Keep:

```bash
./bin/skills-install codex --user
```

for flat skills. Add:

```bash
./bin/skills-install codex --plugins --user
./bin/skills-install codex --plugins --project
```

Native plugin installation copies plugin directories and marketplace metadata into isolated destination roots without installing agent templates automatically.

- [ ] **Step 5: Generate committed Codex output**

Run: `./bin/skills-export sync codex`

Expected: eleven directories under `plugins/codex/` and eleven marketplace entries.

- [ ] **Step 6: Run full automated suite**

Run: `python -m pytest tools/skills-export/tests -m "not integration" -v`

Expected: PASS.

Run: `./bin/skills-export validate && ./bin/skills-export validate codex`

Expected: both PASS.

- [ ] **Step 7: Commit wiring and generated artifacts**

```bash
git add tools/skills-export/skills_export bin/skills-install plugins/codex .agents/plugins/marketplace.json tools/skills-export/tests
git commit -m "feat: wire native Codex plugin pipeline"
```

## Task 11: Document, test with Codex, and finalize

**Files:**
- Modify: `README.md`
- Modify: `adapters/codex/README.md`
- Modify: `plugins/README.md`
- Modify: `tools/skills-export/README.md`
- Modify: `landing/README.md`
- Modify: `CHANGELOG.md`
- Create: `tools/skills-export/tests/integration/test_codex_cli.py`

- [ ] **Step 1: Add opt-in Codex CLI integration tests**

Use temporary `HOME`, `CODEX_HOME`, and repository directories. Skip with a precise reason when `codex` is unavailable. Test local marketplace inspection/discovery, plugin manifest loading, skill visibility, hook parsing, and project-scoped agent installation without mutating real user configuration.

- [ ] **Step 2: Update architecture documentation**

Document:

- `plugins/cursor/` and `plugins/codex/` as committed native outputs;
- `dist/claude` and `dist/codex/skills` as flat skill exports;
- `.agents/plugins/marketplace.json`;
- adapter authoring and regeneration;
- explicit hook trust review;
- explicit custom-agent installation;
- data handling and non-claims for all five workflow plugins.

- [ ] **Step 3: Run end-to-end regeneration**

Run:

```bash
./bin/skills-maintain
git diff --exit-code plugins/cursor plugins/codex .cursor-plugin/marketplace.json .agents/plugins/marketplace.json
```

Expected: maintain succeeds and a second generation produces no diff.

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tools/skills-export/tests -v`

Expected: unit and scenario tests PASS; Codex integration tests PASS when CLI support is available or SKIP with the explicit availability reason.

- [ ] **Step 5: Run repository validation**

Run:

```bash
./bin/skills-export validate
./bin/skills-export validate codex
git diff --check
```

Expected: all commands PASS.

- [ ] **Step 6: Review implementation against the specification**

Check every design requirement has a corresponding generated artifact or test. Search for obsolete claims:

```bash
rg -n 'bundle\.json|@\.agents/instructions\.md|Codex bundle' README.md adapters plugins tools
```

Expected: no documentation describes legacy bundles as native plugins.

- [ ] **Step 7: Commit documentation and integration validation**

```bash
git add README.md adapters/codex/README.md plugins/README.md tools/skills-export/README.md landing/README.md CHANGELOG.md tools/skills-export/tests/integration
git commit -m "docs: document native Codex workflows"
```
