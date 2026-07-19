from __future__ import annotations

from pathlib import Path

import yaml


WORKFLOW_SKILLS = {
    "agentic-trust-gate": [
        "assess-repository-trust",
        "review-mcp-drift",
    ],
    "agent-attack-replay": [
        "build-attack-scenario",
        "run-agent-attack-replay",
    ],
    "crypto-change-radar": [
        "build-crypto-inventory",
        "review-crypto-delta",
        "plan-pqc-migration",
        "test-crypto-interoperability",
    ],
    "entropy-flight-recorder": [
        "qualify-entropy-source",
        "review-entropy-change",
    ],
    "scientific-claim-ledger": [
        "capture-scientific-run",
        "audit-scientific-claim",
        "challenge-sciml-model",
    ],
}


def test_manifest_registers_workflow_plugins() -> None:
    root = Path(__file__).parents[3]
    manifest = yaml.safe_load(
        (root / "core" / "manifest.yaml").read_text(encoding="utf-8")
    )

    for name, skills in WORKFLOW_SKILLS.items():
        plugin = manifest["plugins"][name]
        assert plugin["skills"] == skills
        assert plugin["version"] == "0.1.0"
        assert plugin["codex"] == {"agents": True, "hooks": True}
        for key in (
            "display_name",
            "description",
            "category",
            "keywords",
            "tags",
        ):
            assert plugin[key]


def test_every_plugin_declares_codex_metadata() -> None:
    root = Path(__file__).parents[3]
    manifest = yaml.safe_load(
        (root / "core" / "manifest.yaml").read_text(encoding="utf-8")
    )

    assert len(manifest["plugins"]) == 11
    assert all("codex" in plugin for plugin in manifest["plugins"].values())


def test_landing_assigns_each_workflow_skill() -> None:
    root = Path(__file__).parents[3]
    registry = yaml.safe_load(
        (root / "landing" / "registry.yaml").read_text(encoding="utf-8")
    )

    expected = {
        skill: plugin
        for plugin, skills in WORKFLOW_SKILLS.items()
        for skill in skills
    }
    assignments = registry["assignments"]
    for skill, plugin in expected.items():
        assert assignments.get(skill) == plugin
    # Non-workflow portable skills may also appear in assignments.
    assert assignments.get("agent-ste") == "agent-platform"
    assert registry.get("new_plugins") in (None, {})
