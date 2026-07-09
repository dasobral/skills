# Rust Systems Engineering Review: service.rs

**Date**: 2026-03-13
**Scope**: HTTP service implementation — startup, store access, request processing
**Files reviewed**: `examples/input/service.rs`

---

## CRITICAL Findings

### [CRITICAL] — `.unwrap()` in library code (×3)

**File**: `service.rs:39–43`

```rust
pub fn get_value(key: &str) -> String {
    let store = STORE.lock().unwrap();
    store.as_ref().unwrap().get(key).unwrap().clone()
}
```

**Problem**: Three `.unwrap()` calls in a `pub` library function. Any of
these will panic in the caller's runtime context — a missing key, a poisoned
mutex, or an uninitialised store causes the whole process to crash with no
actionable error.

**Fix**: Return `Result` with a typed error; propagate with `?`:

```rust
#[derive(Debug, thiserror::Error)]
pub enum StoreError {
    #[error("mutex poisoned")]
    Poisoned,
    #[error("store not initialised")]
    Uninitialised,
    #[error("key not found: {0}")]
    KeyNotFound(String),
}

pub fn get_value(key: &str) -> Result<String, StoreError> {
    let store = STORE.lock().map_err(|_| StoreError::Poisoned)?;
    let map = store.as_ref().ok_or(StoreError::Uninitialised)?;
    map.get(key)
        .cloned()
        .ok_or_else(|| StoreError::KeyNotFound(key.to_owned()))
}
```

---

### [CRITICAL] — `serde_json::Value` crossing a function boundary

**File**: `service.rs:49–54`

```rust
pub fn process_request(payload: serde_json::Value) -> serde_json::Value {
    let name = payload["name"].as_str().unwrap_or("unknown");
    serde_json::json!({ "greeting": format!("Hello, {}!", name) })
}
```

**Problem**: Untyped `Value` accepted and returned across a public function
boundary. This makes the contract invisible (what fields are required?),
bypasses compile-time validation, and allows partially valid payloads to
silently produce incorrect results.

**Fix**: Define typed request/response structs:

```rust
#[derive(Debug, serde::Deserialize)]
pub struct GreetRequest {
    pub name: String,
}

#[derive(Debug, serde::Serialize)]
pub struct GreetResponse {
    pub greeting: String,
}

pub fn process_request(req: GreetRequest) -> GreetResponse {
    GreetResponse { greeting: format!("Hello, {}!", req.name) }
}
```

---

## WARNING Findings

### [WARNING] — Not using Axum; no async runtime

**File**: `service.rs:11`, `service.rs:22`

**Problem**: The service uses raw standard library types instead of Axum, and
`main()` is synchronous. All HTTP server code must use Axum with
`#[tokio::main]`.

**Fix** (entry point skeleton):

```rust
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Init tracing
    tracing_subscriber::fmt().json().init();

    let app = axum::Router::new()
        .route("/greet", axum::routing::post(greet_handler))
        .route("/healthz", axum::routing::get(|| async { "ok" }));

    let listener = tokio::net::TcpListener::bind(
        std::env::var("BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:8080".into())
    ).await?;

    axum::serve(listener, app).await?;
    Ok(())
}
```

---

### [WARNING] — `println!` in production code path

**File**: `service.rs:18–20`

```rust
fn log_message(msg: &str) {
    println!("{}", msg);
}
```

**Problem**: `println!` bypasses structured logging. In daemon processes,
output must be newline-delimited JSON to stdout via `tracing`.

**Fix**:

```rust
// Replace every log_message(...) call with:
tracing::info!(message = %msg, "service event");
// Or for structured fields:
tracing::info!(key = %key, "value retrieved");
```

---

### [WARNING] — No graceful shutdown; no health endpoints

**File**: `service.rs:30` (shutdown), `service.rs:22` (no health routes)

**Problem**: The service has no SIGTERM handler and no `/healthz`/`/readyz`
endpoints. Per coding standards, every daemon binary must implement both.

**Fix** (graceful shutdown pattern):

```rust
let token = tokio_util::sync::CancellationToken::new();
let shutdown_token = token.clone();

tokio::spawn(async move {
    tokio::signal::ctrl_c().await.ok();
    shutdown_token.cancel();
});

axum::serve(listener, app)
    .with_graceful_shutdown(token.cancelled())
    .await?;
```

---

### [WARNING] — Hardcoded address; no env-var config

**File**: `service.rs:32`

```rust
let _addr: SocketAddr = "0.0.0.0:8080".parse().unwrap();
```

**Problem**: Address is hardcoded. Config must be loaded from environment
variables at startup with a clear error if required vars are missing.

**Fix**:

```rust
let bind_addr = std::env::var("BIND_ADDR")
    .context("BIND_ADDR environment variable not set")?;
let listener = tokio::net::TcpListener::bind(&bind_addr).await
    .with_context(|| format!("Failed to bind to {bind_addr}"))?;
```

---

### [WARNING] — Raw primitive used as domain ID; no newtype

**File**: `service.rs:60`

```rust
pub fn fetch_user(id: u64) -> Option<String>
```

**Problem**: `u64` is used as a user ID. Without a newtype wrapper, the
compiler cannot distinguish a user ID from any other `u64` (an order ID,
a timestamp, etc.).

**Fix**:

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct UserId(uuid::Uuid);

pub fn fetch_user(id: UserId) -> Option<User> { ... }
```

---

### [WARNING] — Error type returns `String`; no typed error enum

**File**: `service.rs:56`

```rust
pub fn parse_id(s: &str) -> Result<u64, String>
```

**Problem**: `String` errors in library code cannot be matched on by callers.
Library crates must use `thiserror` to define typed, matchable error enums.

**Fix**:

```rust
#[derive(Debug, thiserror::Error)]
pub enum ParseError {
    #[error("invalid ID format: {source}")]
    InvalidFormat { #[from] source: std::num::ParseIntError },
}

pub fn parse_id(s: &str) -> Result<u64, ParseError> {
    Ok(s.parse::<u64>()?)
}
```

---

## SUGGESTION Findings

### [SUGGESTION] — Global `Mutex<Option<HashMap>>` is an anti-pattern

**File**: `service.rs:13`

**Recommendation**: Replace the global store with an Axum `State<S>` extracted
via `Arc`. This makes dependencies explicit, testable, and avoids static
initialisation complexity.

```rust
#[derive(Clone)]
struct AppState {
    store: Arc<tokio::sync::RwLock<HashMap<String, String>>>,
}

async fn greet_handler(
    axum::extract::State(state): axum::extract::State<AppState>,
    axum::extract::Json(req): axum::extract::Json<GreetRequest>,
) -> axum::extract::Json<GreetResponse> { ... }
```

---

## Summary Scorecard

| Category | Issues | Highest severity |
|----------|--------|-----------------|
| Unwrap in library code | 3 | CRITICAL |
| Untyped JSON boundary | 1 | CRITICAL |
| No Axum / no async runtime | 1 | WARNING |
| println! in production path | 1 | WARNING |
| No graceful shutdown / health endpoints | 1 | WARNING |
| Hardcoded config | 1 | WARNING |
| No newtype wrappers | 1 | WARNING |
| String error type | 1 | WARNING |
| Suggestions | 1 | SUGGESTION |
| **TOTAL** | **11** | **CRITICAL** |

**Overall Risk Rating**: 🔴 HIGH — 2 CRITICAL findings present.

---

*Generated by the `rust-systems-engineer` skill.*
*Re-run `/rust-systems-engineer` after applying fixes.*
