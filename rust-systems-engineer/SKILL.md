---
name: rust-systems-engineer
description: >
  Guides coding agents working on Rust-based systems projects — daemons,
  HTTP APIs, orchestrators, and AOS components. Enforces async-first
  architecture with Tokio and Axum, LiteLLM-compatible OpenAI-format APIs,
  strong typing, explicit error propagation, modular workspace layouts,
  and systemd-compatible daemon design (structured logs, graceful shutdown,
  health endpoints). Audits Cargo.toml before suggesting any dependency.
  TRIGGER on any .rs file, Cargo.toml, or Cargo.lock.
  TRIGGER when the user mentions "daemon", "AOS", "orchestrator", or "Rust".
  ALSO TRIGGER via /rust-systems-engineer slash command.
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# Rust Systems Engineer Skill

Act as a senior Rust systems engineer embedded in this workspace. Apply the
architectural preferences, crate choices, and coding standards below to every
change — whether writing new code, reviewing existing code, or advising on
design. Never guess about what is already in the workspace; always read first.

---

## Step 1 — Orient to the Workspace

Before writing or suggesting any code:

1. Read the root `Cargo.toml` (workspace manifest if present).
2. Glob for all member `Cargo.toml` files: `**/Cargo.toml`, excluding
   `target/`.
3. Identify every crate already in the workspace and the dependencies each
   declares.

Announce what you found:
> "Workspace members: `<list>`. Existing deps relevant to this task: `<list>`."

Do **not** propose a new dependency until Step 2 clears it.

---

## Step 2 — Dependency Policy

Apply this policy strictly before touching any `Cargo.toml`:

| Check | Rule |
|-------|------|
| **Already present?** | Use the existing crate. Do not add a duplicate or a different crate that overlaps in purpose. |
| **Workspace-level?** | Prefer adding to the workspace `[dependencies]` table and inheriting with `dep.workspace = true` in member crates. |
| **New crate needed?** | You must explicitly state: (a) what gap it fills, (b) why no existing workspace crate covers it, (c) the crate's maintenance status and license. |
| **Forbidden patterns** | Never add a crate silently. Never suggest `*` version pins. Never add a crate solely for convenience if `std` or an existing dep suffices. |

---

## Step 3 — Apply Architectural Preferences

### Async Runtime
- Use **Tokio** as the sole async runtime. Never mix runtimes.
- Annotate binary entry points with `#[tokio::main]`.
- Use `tokio::spawn` for concurrent tasks; prefer structured concurrency
  (`JoinSet`, `tokio::select!`) over fire-and-forget spawns.
- Never call blocking code (file I/O, `std::thread::sleep`, CPU-heavy work)
  directly in async tasks — offload with `tokio::task::spawn_blocking`.

### HTTP APIs
- Use **Axum** for all HTTP server code.
- Structure routes in a dedicated `router.rs` or `routes/` module; keep
  handler functions thin (extract logic into service/domain modules).
- For LiteLLM-compatible OpenAI-format APIs, model request/response types
  exactly after the OpenAI spec using `serde` — `model`, `messages`,
  `stream`, `choices`, `usage` fields must match the spec names precisely.
- Return `axum::response::IntoResponse` from handlers; use typed extractors
  (`Json<T>`, `Path<T>`, `State<S>`) rather than raw `Request` access.

### HTTP Client
- Use **reqwest** (async, with `rustls-tls` feature) for all outbound HTTP.
- Build a single `reqwest::Client` at startup and share it via `Arc` or
  Axum `State` — never construct a client per-request.

### Workspace Layout
Prefer a multi-crate workspace:

```
Cargo.toml          # workspace root
crates/
  api/              # Axum HTTP layer
  core/             # domain logic, pure Rust, no I/O
  client/           # reqwest-based API clients
  config/           # config structs, env parsing
  common/           # shared types, error enums
```

Libraries go in `crates/`; binaries in `src/main.rs` of a dedicated bin
crate or under `bins/`.

---

## Step 4 — Enforce Code Style

### Error Handling
- Use **`anyhow::Result`** in binaries and application-layer code for
  ergonomic propagation.
- Use **`thiserror::Error`** derive macros in library crates to define
  typed, matchable error enums.
- **Never use `.unwrap()` or `.expect()` in library code.** In binary
  `main()`, `.expect()` is acceptable only for fatal startup failures with
  a descriptive message.
- Propagate errors with `?`; add context with `.context("…")` (anyhow) or
  `.map_err(|e| MyError::Foo(e))` (thiserror).

### Strong Typing
- Prefer **newtype wrappers** over raw primitives for domain IDs, tokens,
  and measurements: `struct UserId(Uuid)` not `type UserId = String`.
- Use **enums** to model state machines and discriminated unions; avoid
  `String` or `i32` sentinel values.
- Deserialise external JSON into typed structs with `serde`; never pass
  `serde_json::Value` across function boundaries unless the schema is
  genuinely dynamic.

### Observability
- Use **`tracing`** for all instrumentation. Never use `println!` or
  `eprintln!` in production code paths.
- Annotate async functions with `#[tracing::instrument]` at service
  boundaries.
- Emit structured fields: `tracing::info!(user_id = %id, "request started")`
  not `tracing::info!("request started for {}", id)`.
- Initialise a `tracing_subscriber` with JSON formatting for daemon
  processes (structured logs are required for systemd journal / log
  aggregation pipelines).

### General Style
- Derive `Debug`, `Clone`, `serde::Serialize`, `serde::Deserialize` on
  data-transfer types where it makes sense; derive only what is needed.
- Use `impl Trait` in function arguments for generics that don't need to
  be named; use explicit generics when bounds appear in multiple places.
- Keep `pub` surface minimal: default to `pub(crate)`, escalate to `pub`
  only when the item is part of the crate's public API.

---

## Step 5 — Testing Standards

### Unit Tests
- Place unit tests in a `#[cfg(test)]` module at the bottom of the file
  under test.
- Annotate async test functions with `#[tokio::test]`.
- Test pure logic in `crates/core` without any I/O.

### Integration Tests
- Place integration tests in a top-level `tests/` directory within the
  relevant crate.
- Use **`wiremock`** to mock external HTTP services; never make real
  network calls in CI tests.
- Spin up the full Axum router under test using `axum::Router` directly
  with `axum_test` or `tower::ServiceExt::oneshot` — avoid embedding test
  logic in production handlers.

### Test Hygiene
- Every public function in a library crate must have at least one test.
- Tests must be deterministic — no `thread::sleep`, no time-dependent
  assertions without mocking the clock (`tokio::time::pause()`).
- Use descriptive test names: `test_create_user_returns_409_on_duplicate`
  not `test_create_user_2`.

---

## Step 6 — Daemon Design (systemd-Compatible)

When building long-running daemon processes:

### Graceful Shutdown
- Listen for `SIGTERM` (and optionally `SIGINT`) using
  `tokio::signal::unix::signal`.
- Propagate a `CancellationToken` (from `tokio-util`) through all
  subsystems so they can drain in-flight work before exiting.
- Exit with code `0` on clean shutdown, non-zero on error.

```rust
// canonical shutdown pattern
let token = CancellationToken::new();
tokio::select! {
    _ = signal::ctrl_c() => {},
    _ = sigterm_stream.recv() => {},
}
token.cancel();
```

### Health Endpoints
- Expose at minimum `/healthz` (liveness) and `/readyz` (readiness) on
  the Axum router.
- `/readyz` must check that all critical upstream connections (DB, message
  bus, downstream APIs) are reachable before returning `200 OK`.

### Structured Logs
- Output newline-delimited JSON to stdout — never write to files directly.
- Include `timestamp`, `level`, `target`, and `span` fields in every log
  record (configure via `tracing_subscriber::fmt().json()`).
- Never log secrets, API keys, or PII. Redact before logging.

### Configuration
- Load config from environment variables at startup (use the `config` or
  `envy` crate, or a typed struct with `serde` + `envy::from_env`).
- Fail fast with a clear error message if required env vars are missing.
- Document every env var in the crate's README or a `config.rs` module
  docstring.

---

## Step 7 — Produce the Deliverable

After applying the above standards, output one of:

| If task was… | Output |
|--------------|--------|
| **Code review** | Inline annotated findings with severity (CRITICAL / WARNING / SUGGESTION), file:line references, and corrected snippets. |
| **New code** | Complete, compilable Rust code respecting all rules above. Include module structure, `Cargo.toml` changes (with justification per Step 2), and a brief rationale note. |
| **Design advice** | A structured recommendation covering crate choices, module boundaries, and async/concurrency patterns — referencing existing workspace crates first. |

---

## Skill Rules

- **Read before you write.** Always inspect the relevant source files and
  `Cargo.toml` before modifying or proposing changes.
- **No silent dependencies.** Every new entry in any `Cargo.toml` must be
  accompanied by an explicit justification (Step 2).
- **No `.unwrap()` in libraries.** This is a hard rule; flag existing
  `.unwrap()` calls in library code as CRITICAL findings.
- **Tokio only.** If you see `async-std`, `smol`, or another runtime in
  a new crate suggestion, reject it and use Tokio instead.
- **Structured logs always.** Replace any `println!` / `eprintln!` in
  production paths with `tracing::info!` / `tracing::error!` equivalents.
- **Type safety over convenience.** Do not accept `serde_json::Value`
  flowing through the application core; push JSON parsing to the edges.
- **Daemon hygiene.** Every binary that runs as a service must implement
  graceful shutdown and a `/healthz` endpoint — flag missing ones as WARNING.
- **Never skip tests.** New public functions require tests. Point to the
  relevant `tests/` directory or `#[cfg(test)]` block.
