// ── service.rs ────────────────────────────────────────────────────────────────
// Example Rust HTTP service with deliberate defects for review practice.
// This is NOT production-quality code — it is an input for the
// rust-systems-engineer skill review workflow.
// ─────────────────────────────────────────────────────────────────────────────

use std::collections::HashMap;
use std::sync::Mutex;

// [DEFECT R1] Not using Axum — raw http types instead.
// Rule: all HTTP server code must use Axum.
use std::net::SocketAddr;

// [DEFECT R2] Untyped global mutable state — HashMap<String, String> instead
// of a typed struct. No newtype wrappers.
static STORE: Mutex<Option<HashMap<String, String>>> = Mutex::new(None);

// [DEFECT R3] println! in production code path.
// Rule: use tracing::info! / tracing::error! exclusively.
fn log_message(msg: &str) {
    println!("{}", msg);
}

// [DEFECT R4] No async runtime annotation. Entry point is synchronous.
// Rule: binaries use #[tokio::main].
fn main() {
    // [DEFECT R5] Initialising global state via .unwrap() with no error message.
    // Rule: in binary main(), .expect() is acceptable for fatal startup with a
    // descriptive message. Raw .unwrap() is forbidden.
    let mut store = STORE.lock().unwrap();
    *store = Some(HashMap::new());
    drop(store);

    log_message("Service started");  // [DEFECT R3] println! indirection

    // [DEFECT R6] Hardcoded address and port with no config from environment.
    // Rule: load config from env vars at startup; fail fast with a clear error.
    let _addr: SocketAddr = "0.0.0.0:8080".parse().unwrap();  // [DEFECT R5]

    // [DEFECT R7] No graceful shutdown signal handling.
    // Rule: daemons must listen for SIGTERM and propagate CancellationToken.

    // [DEFECT R8] No health endpoints.
    // Rule: every daemon binary must expose /healthz and /readyz.
}

// [DEFECT R9] Library function uses .unwrap() — CRITICAL violation.
// Rule: never .unwrap() in library code.
pub fn get_value(key: &str) -> String {
    let store = STORE.lock().unwrap();  // CRITICAL: unwrap in library code
    store
        .as_ref()
        .unwrap()  // CRITICAL: second unwrap
        .get(key)
        .unwrap()  // CRITICAL: third unwrap — panics if key absent
        .clone()
}

// [DEFECT R10] serde_json::Value flowing through function boundary.
// Rule: deserialise into typed structs; never pass Value across boundaries.
pub fn process_request(payload: serde_json::Value) -> serde_json::Value {
    // [DEFECT R11] No input validation before accessing fields.
    let name = payload["name"].as_str().unwrap_or("unknown");  // [DEFECT R9]
    serde_json::json!({ "greeting": format!("Hello, {}!", name) })
}

// [DEFECT R12] Error type uses String — not a typed thiserror enum.
// Rule: library crates define typed, matchable error enums with thiserror.
pub fn parse_id(s: &str) -> Result<u64, String> {
    s.parse::<u64>().map_err(|e| e.to_string())
}

// [DEFECT R13] Raw u64 used as an ID — no newtype wrapper.
// Rule: prefer newtype wrappers for domain IDs: struct UserId(u64)
pub fn fetch_user(id: u64) -> Option<String> {
    let _ = id;
    None
}
