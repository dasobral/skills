# Agent STE — Transformation Examples

Each example shows Human instruction → Agent STE, then why the rewrite is superior.

---

## 1) Coding task

**Human:**  
`Optimize the user search endpoint and improve error handling as needed.`

**Agent STE:**

```text
OBJECTIVE: Reduce P95 latency of EP-GET-/v1/users/search and return structured errors for invalid queries.

ENTITIES:
- AGENT-worker (actor)
- EP-GET-/v1/users/search (endpoint in SVC-api)
- FILE-src/handlers/user_search.ts
- FILE-src/errors/http_error.ts
- TEST-user-search (jest suite)

GLOSSARY:
- latency = server-side handler duration excluding client network
- structured error = JSON {code, message, fields?} with correct HTTP status

SCOPE.IN: FILE-src/handlers/user_search.ts, FILE-src/errors/http_error.ts, TEST-user-search
SCOPE.OUT: database schema, authentication, unrelated endpoints

ASSUMPTIONS:
- Baseline P95 is 800ms in ENV-staging over last 7 days ; IF FALSE → measure first, then set target

CONSTRAINTS:
- No response-field removals
- Keep HTTP 200 for successful searches

PRECONDITIONS:
- `git status` clean on BRANCH-feat-user-search
- ENV-staging metrics readable

ORDERED ACTIONS:
1. AGENT-worker measure baseline P95 for EP-GET-/v1/users/search in ENV-staging.
2. AGENT-worker change FILE-src/handlers/user_search.ts to remove N+1 query pattern identified in step 1.
3. AGENT-worker change FILE-src/errors/http_error.ts so invalid query params return HTTP 400 with structured error.
4. AGENT-worker add/update TEST-user-search for latency-sensitive path and 400 cases.
5. AGENT-worker run VALIDATION.

SUCCESS CRITERIA:
- P95 ≤ 400ms on ENV-staging for 15-minute window after deploy-to-staging
- TEST-user-search exit code 0
- Invalid query returns HTTP 400 with JSON keys code,message

FAILURE CONDITIONS:
- P95 > 400ms after one optimization pass → abort feature merge; keep measurement artifact
- Tests fail → do not deploy

ROLLBACK: `git revert` the merge commit on BRANCH-main if staging P95 > baseline
IDEMPOTENCY: SAFE TO RE-RUN: yes — remeasure then reapply only if tests fail
```

**Why superior:** Replaces `optimize`/`improve`/`as needed` with a metric, files, tests, failure branches, and rollback.

---

## 2) DevOps task

**Human:**  
`Fix the flaky tests somehow and clean up the CI pipeline.`

**Agent STE:**

```text
OBJECTIVE: Make JOB-ci-unit pass three consecutive runs on BRANCH-main with no ignored tests added.

ENTITIES: AGENT-devops, JOB-ci-unit, FILE-.github/workflows/ci.yml, DIR-tests/
SCOPE.IN: JOB-ci-unit definition, failing test files listed in ARTIFACT-flake-report
SCOPE.OUT: JOB-ci-deploy, renames of unrelated workflows

ORDERED ACTIONS:
1. AGENT-devops collect last 20 JOB-ci-unit runs; write ARTIFACT-flake-report (test name, fail rate).
2. AGENT-devops for each test with fail rate ≥ 10%: remove shared mutable state OR isolate with unique temp dirs.
3. AGENT-devops delete redundant steps in FILE-.github/workflows/ci.yml only if step name ∈ {setup-node-duplicate, cache-npm-old}.
4. AGENT-devops run JOB-ci-unit three times on the same commit.

SUCCESS CRITERIA:
- Three consecutive JOB-ci-unit runs exit 0 on commit SHA-X
- Fail rate of previously flaky tests < 1% over those three runs
- No new `test.skip` / `xit` / `allow_failure: true` introduced

FAILURE: Any skip-based “fix” → abort and escalate to HUMAN-maintainer
ROLLBACK: Revert workflow + test commits if BRANCH-main goes red
```

**Why superior:** Removes `somehow`/`clean up`; defines flake threshold, banned fake fixes, and a closed set of CI deletions.

---

## 3) Documentation task

**Human:**  
`Update the docs to be better and add examples where appropriate.`

**Agent STE:**

```text
OBJECTIVE: Make FILE-docs/api.md match OpenAPI SPEC-openapi.yaml@sha-abc123 and include one request/response example per endpoint.

SCOPE.IN: FILE-docs/api.md
SCOPE.OUT: marketing pages, changelog tone edits

ORDERED ACTIONS:
1. AGENT-docs diff endpoint list in SPEC-openapi.yaml vs FILE-docs/api.md.
2. AGENT-docs update every mismatched path/method/status code in FILE-docs/api.md.
3. AGENT-docs add exactly one example pair (request + response) under each endpoint section.
4. AGENT-docs run `npm run docs:linkcheck` and `npm run docs:openapi-sync`.

SUCCESS CRITERIA:
- `npm run docs:openapi-sync` exit 0
- Endpoint count in docs == endpoint count in SPEC-openapi.yaml
- Each endpoint section contains headings Example Request and Example Response

ROLLBACK: NONE required if commit isolated; else `git revert`
```

**Why superior:** `better`/`appropriate` become sync-with-spec plus countable examples and commands.

---

## 4) Git workflow

**Human:**  
`Push when ready after cleaning up the history a bit.`

**Agent STE:**

```text
OBJECTIVE: Publish BRANCH-feat-cache to ORIGIN as a reviewable PR against BRANCH-main with linear commits.

PRECONDITIONS:
- All tests in JOB-local-unit exit 0
- No secrets in `git grep -I -E 'API_KEY|BEGIN RSA'`

ORDERED ACTIONS:
1. AGENT-git rebase BRANCH-feat-cache onto ORIGIN/BRANCH-main.
2. AGENT-git squash fixup commits into logical commits ≤ 3 total; commit messages must match `^feat:|^fix:|^docs:`.
3. AGENT-git push --force-with-lease ORIGIN BRANCH-feat-cache.
4. AGENT-git open PR to BRANCH-main with template FILE-.github/pull_request_template.md filled.

SUCCESS CRITERIA:
- PR URL returned
- CI JOB-ci-unit status is pending or pass on the PR head
- Commit count on PR ≤ 3

FAILURE: force-with-lease rejected → abort and ask HUMAN
ROLLBACK: Do not delete remote branch; leave PR closed if opened in error
```

**Why superior:** `when ready`/`a bit` become preconditions, commit policy, and exact git operations.

---

## 5) Research task

**Human:**  
`Look into vector databases and tell me what we should use.`

**Agent STE:**

```text
OBJECTIVE: Recommend one vector database for PROJECT-search among {pgvector, qdrant, milvus} with scored evidence.

INPUTS:
- REQ-latency P95 ≤ 50ms at 1M vectors dim=768
- REQ-ops team skill = PostgreSQL
- BUDGET-infra ≤ $500/month estimated

ORDERED ACTIONS:
1. AGENT-research gather primary docs + one independent benchmark source per candidate.
2. AGENT-research score each candidate 0–5 on {latency, ops-fit, cost, ecosystem}.
3. AGENT-research select the highest total; break ties by ops-fit.
4. AGENT-research write ARTIFACT-recommendation.md with scores, citations, and risks.

SUCCESS CRITERIA:
- Artifact contains scores table and exactly one winner
- Every score cites a URL or benchmark file
- Explicit NON-GOALS listed

FAILURE: Insufficient sources for a candidate → mark candidate UNKNOWN, do not score from memory
```

**Why superior:** Open-ended “look into” becomes a closed candidate set, constraints, and citation-backed decision rule.

---

## 6) Debugging session

**Human:**  
`Users say login is broken sometimes. Figure it out.`

**Agent STE:**

```text
OBJECTIVE: Identify root cause of intermittent HTTP 5xx on EP-POST-/v1/login and land a failing test plus fix OR a confirmed external dependency incident report.

INPUTS: LOG-source ENV-prod last 24h; METRIC-login-error-rate
PRECONDITIONS: Read-only access to LOG-source until root cause hypothesis written

ORDERED ACTIONS:
1. AGENT-debug quantify error rate and top exception signatures from LOG-source.
2. AGENT-debug form ≤2 hypotheses with distinguishing predictions.
3. AGENT-debug test hypotheses in ENV-staging with reproduction script FILE-scripts/repro_login.sh.
4. IF code defect confirmed THEN write TEST-login-race that fails before fix and passes after fix.
5. IF dependency incident confirmed THEN write ARTIFACT-incident.md and stop code changes.

SUCCESS CRITERIA:
- Either (TEST-login-race + fix merged) OR (ARTIFACT-incident.md with dependency, timeline, next action)
- METRIC-login-error-rate < 0.5% for 1h in ENV-staging after fix, if code path chosen

INVARIANT: No production secret values copied into the repo
```

**Why superior:** “Sometimes/figure it out” becomes measurement → hypotheses → repro → code-or-incident fork with invariants.

---

## 7) Infrastructure deployment

**Human:**  
`Deploy the new version carefully to prod.`

**Agent STE:**

```text
OBJECTIVE: Deploy IMAGE-api:2.4.1 to ENV-prod with canary then full rollout.

PRECONDITIONS:
- IMAGE-api:2.4.1 exists in REGISTRY
- JOB-ci-unit and JOB-ci-e2e green on TAG-v2.4.1
- Change window OPEN (HUMAN-oncall approved)

ORDERED ACTIONS:
1. AGENT-sre set canary weight 10% on SVC-api in ENV-prod.
2. AGENT-sre watch METRIC-error-rate and METRIC-p95 for 20 minutes.
3. IF METRIC-error-rate ≤ 1% AND METRIC-p95 ≤ 300ms THEN set canary weight 100%.
4. ELSE run ROLLBACK.

SUCCESS CRITERIA:
- SVC-api in ENV-prod runs IMAGE-api:2.4.1 at 100% weight
- METRIC-error-rate ≤ 1% and METRIC-p95 ≤ 300ms for 20 minutes post-full rollout

FAILURE CONDITIONS:
- error-rate > 1% OR p95 > 300ms during canary → ROLLBACK immediately

ROLLBACK:
1. Set traffic to previous IMAGE-api:2.4.0 at 100%.
2. Verify error-rate ≤ 1% for 10 minutes.
3. Page HUMAN-oncall if still elevated.

PERMISSIONS: role deploy-prod
SIDE EFFECTS: user traffic shift; possible brief cache misses
IDEMPOTENCY: SAFE TO RE-RUN: no for traffic steps without checking current weight first
```

**Why superior:** `carefully` becomes canary percentages, metric gates, and explicit rollback.

---

## 8) Security review

**Human:**  
`Do a security review and harden things appropriately.`

**Agent STE:**

```text
OBJECTIVE: Produce ARTIFACT-security-review.md for REPO-app covering OWASP ASVS L2 authentication and dependency CVEs, and remediate only CRITICAL/HIGH items that have proven fixes.

SCOPE.IN: auth routes, session handling, DEPENDENCY-lockfile
SCOPE.OUT: LOW findings, UI copy, performance

ORDERED ACTIONS:
1. AGENT-sec run `npm audit --omit=dev` and SAST tool TOOL-semgrep with ruleset OWASP-top-10.
2. AGENT-sec review FILE-src/auth/** against checklist CHK-asvs-l2-auth.
3. AGENT-sec write ARTIFACT-security-review.md with finding ID, severity, evidence, recommendation.
4. AGENT-sec patch CRITICAL/HIGH findings that have a vendor-fixed version or ≤20-LOC code fix.
5. AGENT-sec re-run tools; verify CRITICAL/HIGH count = 0 OR remaining items listed as ACCEPTED-RISK with HUMAN-sec owner.

SUCCESS CRITERIA:
- Artifact exists with finding table
- No CRITICAL/HIGH without fix commit or ACCEPTED-RISK row
- `npm audit --omit=dev` shows 0 critical and 0 high, or accepted risks documented

FORBIDDEN FAKE HARDENING: adding headers without verifying route coverage; deleting tests to silence scanners
```

**Why superior:** `harden appropriately` becomes standard, severity gate, artifact, and ban on theater fixes.
