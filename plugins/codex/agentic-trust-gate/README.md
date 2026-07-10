# Agentic Trust Gate

Evidence workflows for repository control-plane inventory and MCP capability-drift review.

## Daily workflow

1. Run `assess-repository-trust` before granting an unfamiliar repository agent capabilities.
2. Hash and classify instructions, hooks, skills, MCP configuration, lifecycle scripts, tasks, containers, symlinks, and executables.
3. Run `review-mcp-drift` against the last approved MCP snapshot.
4. Record dispositions, evidence gaps, reviewer identity, and approval/revocation anchors.

## Triggers

Use on repository onboarding, control-plane changes, MCP server/schema/auth changes, new executable automation, or trust-decision renewal. The hook reports changed control-plane file hashes.

## Required inputs

- Repository identity, immutable revision, scope, and requested capabilities.
- Canonical baseline or prior approved inventory and MCP schemas.
- Reviewer policy, authenticated approval state, and available evidence sources.

## Artifacts

- Trust inventory and hash-linked disposition ledger.
- MCP capability delta covering names, schemas, auth, package identity, scopes, and mutability.
- Approval, revocation, unknown, not-applicable, and evidence-gap records.

## Agent authority

The configuration archaeologist inventories evidence and the capability analyst assesses drift. Neither can grant trust, approve capabilities, alter policy, or conceal evidence gaps.

## Deterministic checks and agent decisions

Canonicalization, path checks, hashes, schema comparisons, and approval-chain validation are deterministic. Source classification, capability risk, and final trust disposition require accountable human review.

## Data guarantees

Contracts bind decisions to repository revision, requested capability, source class, and content hash. The hook is read-only and reports hashes rather than collecting secrets.

## Limitations and non-claims

This plugin does not prove a repository or MCP server is safe, authenticate remote mutable content by itself, or replace sandboxing, least privilege, and independent review.
