# Crate Selection Guide

Reference document for the `rust-systems-engineer` skill.
Use this guide to select the correct crate before touching any `Cargo.toml`.

**Policy reminder**: Always check the workspace's existing `Cargo.toml` first.
If a crate is already present, use it. Never add a duplicate.

---

## Approved Crate Stack

### Async Runtime

| Purpose | Crate | Notes |
|---------|-------|-------|
| Async runtime | `tokio` (features: `full`) | Only runtime. Never mix with `async-std` or `smol`. |
| Structured concurrency | `tokio::task::JoinSet` | Prefer over fire-and-forget spawns. |
| Cancellation | `tokio-util` (feature: `rt`) — `CancellationToken` | Required for graceful shutdown. |

### HTTP Server

| Purpose | Crate | Notes |
|---------|-------|-------|
| HTTP server | `axum` | All HTTP server code. Use typed extractors. |
| Middleware / service layer | `tower` | Works with Axum; use for auth, tracing, rate limiting. |
| HTTP body utilities | `hyper` | Axum dependency — do not add independently unless needed for raw access. |

### HTTP Client

| Purpose | Crate | Notes |
|---------|-------|-------|
| Outbound HTTP | `reqwest` (feature: `rustls-tls`) | Single `Client` at startup, shared via `Arc`/`State`. Never per-request. |

### Serialization

| Purpose | Crate | Notes |
|---------|-------|-------|
| JSON / YAML / TOML serialization | `serde` + `serde_json` | All data transfer types. Never pass `Value` across function boundaries. |
| JSON only | `serde_json` | Only when `serde` is already present. |

### Error Handling

| Purpose | Crate | Library or binary? | Notes |
|---------|----|----|----|
| Application-layer errors | `anyhow` | Binary / app | Ergonomic `Result` propagation with `.context()`. |
| Library-level typed errors | `thiserror` | Library | `#[derive(Error)]` for matchable error enums. |

**Rule**: Never `.unwrap()` in library code. In binary `main()`, `.expect()`
is acceptable for fatal startup failures with a descriptive message.

### Observability

| Purpose | Crate | Notes |
|---------|-------|-------|
| Structured logging / tracing | `tracing` | All instrumentation. Never `println!` in production. |
| Subscriber (JSON output for daemons) | `tracing-subscriber` (feature: `json`) | JSON output to stdout for systemd journal / log aggregation. |
| Span macros | `#[tracing::instrument]` | Annotate async functions at service boundaries. |

### Configuration

| Purpose | Crate | Notes |
|---------|-------|-------|
| Environment-based config | `envy` | Typed struct from env vars via `serde`. |
| Complex config (file + env) | `config` | When multiple config sources needed. |

### Testing

| Purpose | Crate | Notes |
|---------|-------|-------|
| External HTTP mocking | `wiremock` | For integration tests. Never real network calls in CI. |
| Axum router testing | `axum::Router` + `tower::ServiceExt::oneshot` | Avoids embedding test logic in production handlers. |
| Async test | `#[tokio::test]` | Annotate all async test functions. |

### Database (if needed — check alternatives first)

| Purpose | Crate | Notes |
|---------|-------|-------|
| Async SQL | `sqlx` | With `runtime-tokio-rustls` feature. |
| ORM | `sea-orm` | If ORM patterns are needed; otherwise prefer raw `sqlx`. |

### IDs and Types

| Purpose | Crate | Notes |
|---------|-------|-------|
| UUID generation | `uuid` (features: `v4`, `serde`) | For entity IDs. Wrap in newtype: `struct UserId(Uuid)`. |
| Timestamps | `chrono` or `time` | Pick one; do not use both. |

---

## Forbidden / Rejected Crates

| Crate | Reason |
|-------|--------|
| `async-std` | Not Tokio. Reject in any new crate suggestion. |
| `smol` | Not Tokio. Reject in any new crate suggestion. |
| `actix-web` | Not Axum. Do not add unless existing code already uses it. |
| `serde_json::Value` flowing through application core | Use typed structs; push JSON parsing to edges. |
| `failure` | Deprecated. Use `anyhow` / `thiserror`. |
| `error-chain` | Deprecated. Use `anyhow` / `thiserror`. |

---

## Adding a New Crate — Required Justification

Before adding any crate not in this guide, document:

1. **What gap it fills** — what cannot be done with existing workspace crates.
2. **Why no existing dep covers it** — explicit comparison with alternatives.
3. **Maintenance status** — last release date, GitHub stars, MSRV.
4. **License** — must be compatible with the project license.
5. **`version` pin** — must be a specific version (not `*` or `>=`). Prefer
   `"x.y"` (minor-pinned) or `"=x.y.z"` (exact) for production code.

---

## Workspace Dependency Inheritance Pattern

For workspace projects, declare shared deps at the workspace root:

```toml
# workspace Cargo.toml
[workspace.dependencies]
tokio      = { version = "1.40", features = ["full"] }
axum       = { version = "0.7" }
serde      = { version = "1.0", features = ["derive"] }
serde_json = { version = "1.0" }
tracing    = { version = "0.1" }
anyhow     = { version = "1.0" }
thiserror  = { version = "1.0" }
```

```toml
# member crate Cargo.toml
[dependencies]
tokio.workspace      = true
axum.workspace       = true
serde.workspace      = true
```

This prevents version skew across crates and makes upgrades a single edit.
