# Codecraft

Operational code-quality workflows for repository analysis, conformant implementation, review, and debt tracking.

## Daily workflow

1. Run `analyze-codebase` before changing an unfamiliar repository.
2. Use `write-conformant-code` with the discovered conventions and task constraints.
3. Run `review-quality` on the resulting diff and test evidence.
4. Record structural follow-up with `audit-cognitive-debt`.

## Triggers

Use this plugin for repository onboarding, implementation, pull-request review, convention drift, or recurring maintainability problems. The session-start hook only reports stale Codex convention guidance when relevant.

## Required inputs

- Repository path and revision.
- Requested behavior, acceptance criteria, and applicable convention files.
- The diff plus build, lint, and test evidence for review.

## Artifacts

- Codebase analysis and convention summary.
- Conformant code changes and verification evidence.
- Quality review findings and a prioritized cognitive-debt record.

## Agent authority

The convention analyst and code reviewer are advisory templates. They may inspect and report; they do not approve changes, install themselves, or override repository instructions.

## Deterministic checks and agent decisions

Builds, tests, linters, file hashes, and the convention-age hook provide deterministic evidence. Convention interpretation, defect severity, and refactoring priority remain agent judgments for a human owner to accept or reject.

## Data guarantees

The bundled hook reads repository paths and convention-file metadata, emits context, and does not write project files. Review artifacts should cite repository evidence and must not invent test results.

## Limitations and non-claims

This plugin does not guarantee correctness, security, style compliance, or complete debt discovery. Agent templates require explicit installation and a new Codex session.
