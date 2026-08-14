# C++ Production Engineering Review: ws_client.cpp

**Date**: 2026-03-13
**Scope**: WebSocket client implementation
**Files reviewed**: `examples/input/ws_client.cpp`

---

## CRITICAL Findings

### [CRITICAL] [TLS] — TLS certificate verification disabled

**File**: `ws_client.cpp:32`

```cpp
tls_ctx->set_verify_mode(boost::asio::ssl::verify_none); // NEVER in production
```

**Problem**: Setting `verify_none` disables peer certificate verification,
making the connection trivially vulnerable to man-in-the-middle attacks. Any
attacker with network access can intercept key management traffic.

**Fix**:

```cpp
tls_ctx->set_verify_mode(boost::asio::ssl::verify_peer);
tls_ctx->load_verify_file(ca_bundle_path_);  // CA bundle must be a constructor param
```

---

### [CRITICAL] [Security] — Key material potentially logged

**File**: `ws_client.cpp:58`

```cpp
LogManager::instance().log("Send error for payload: " + payload);
```

**Problem**: The `payload` may contain key material or authentication tokens.
Logging it — even in an error path — permanently compromises forward secrecy
and violates the key material logging invariant.

**Fix**:

```cpp
// Log only a non-secret identifier, never the payload content
LogManager::instance().log("Send error on connection " + conn_id_
    + " [tid=" + std::to_string(/* thread id */) + "]");
```

---

### [CRITICAL] [RAII] — Raw owning pointer; memory leak

**File**: `ws_client.cpp:75–76`

```cpp
WebSocketClient* client = new WebSocketClient("wss://example.com/api");
// ... client never deleted
```

**Problem**: Raw owning pointer with no corresponding `delete`. Memory leak on
every run. Ownership is never transferred to a smart pointer.

**Fix**:

```cpp
auto client = std::make_unique<WebSocketClient>("wss://example.com/api");
```

---

## WARNING Findings

### [WARNING] [Concurrency] — Unprotected global mutable state

**File**: `ws_client.cpp:16–17`

```cpp
std::string g_last_message;
bool g_connected = false;
```

**Problem**: Both globals are written from multiple threads (connect handler,
message handler, close handler) with no mutex. This is a data race — undefined
behaviour in C++.

**Fix**: Remove globals. Encapsulate state inside `WebSocketClient` with a
mutex:

```cpp
class WebSocketClient {
    // Protects: last_message_, connected_
    mutable std::mutex state_mutex_;
    std::string last_message_;
    bool connected_{false};
};
```

---

### [WARNING] [Concurrency] — Thread detached with no lifecycle tracking

**File**: `ws_client.cpp:50`

```cpp
std::thread([this]() { client_.run(); }).detach();
```

**Problem**: A detached thread outlives the `WebSocketClient` object that
`this` points to. When the object is destroyed, the detached thread accesses
dangling memory.

**Fix**: Store the thread and join it on destruction with a stop signal:

```cpp
// In class: std::thread run_thread_; std::atomic<bool> stop_{false};
// In connect():
run_thread_ = std::thread([this]() { client_.run(); });
// In destructor (noexcept):
stop_ = true;
client_.stop();
if (run_thread_.joinable()) run_thread_.join();
```

---

### [WARNING] [Concurrency] — Race condition: `g_connected` set before `run()` is active

**File**: `ws_client.cpp:53`

```cpp
g_connected = true; // set before run() completes handshake
```

**Problem**: The `run()` call (which drives the async event loop including the
TLS handshake) is executing in a detached thread. Setting `g_connected = true`
on the caller's thread before the handshake completes is a race — the
connection is not actually live at this point.

**Fix**: Use the websocketpp `open_handler` to set connected state after the
handshake succeeds, under a mutex.

---

### [WARNING] [Networking] — No reconnect logic

**File**: `ws_client.cpp:43–46`

```cpp
client_.set_close_handler([this](ConnectionHdl) {
    g_connected = false;
    LogManager::instance().log("Connection closed");
    // No reconnect
});
```

**Problem**: The connection is never re-established after a close event. For a
production key management system, a dropped connection must trigger reconnect
with exponential back-off.

**Fix**: Implement a `ConnState` machine and a reconnect loop per
coding-standards.md §6:

```cpp
enum class ConnState { Disconnected, Connecting, Connected, Reconnecting };
// On close: transition to Reconnecting, schedule attempt with back-off
```

---

### [WARNING] [Logging] — `LogManager` logs to `std::cout`, no syslog integration

**File**: `ws_client.cpp:28–30`

```cpp
void log(const std::string& msg) {
    std::cout << msg << std::endl;
}
```

**Problem**: Production daemon processes must use `syslog` for log output.
Direct `std::cout` does not integrate with the system journal and lacks ISO
8601 timestamps, facility, component name, or thread ID.

**Fix**: Replace with a syslog wrapper that includes all required fields per
coding-standards.md §5.

---

### [WARNING] [Logging] — No severity filtering in `LogManager`

**File**: `ws_client.cpp:21–31`

**Problem**: `LogManager::log()` has no severity parameter and applies no
level filter. All messages are emitted unconditionally, and the level is a
public `int` with no accessor protection.

**Fix**: Add a `SeverityLevel` enum and runtime-configurable level filter per
coding-standards.md §5.

---

### [WARNING] [RAII] — `LogManager` has a public default constructor

**File**: `ws_client.cpp:20`

**Problem**: The `LogManager` singleton pattern allows the class to be
default-constructed by any caller, breaking the singleton invariant.

**Fix**:

```cpp
private:
    LogManager() = default;
    LogManager(const LogManager&) = delete;
    LogManager& operator=(const LogManager&) = delete;
```

---

## SUGGESTION Findings

### [SUGGESTION] [Networking] — No per-connection receive buffer for partial records

**File**: `ws_client.cpp:62–65`

**Problem**: `on_message` passes the raw `payload` directly to `process()`
with no buffering. If the application-level protocol sends logical records
split across multiple messages, this will silently corrupt data.

**Recommendation**: Maintain a `std::string recv_buffer_` per connection and
append payloads, parsing only when a complete delimiter is found.

---

### [SUGGESTION] [Concurrency] — `ConnectionHdl` not protected by a mutex

**File**: `ws_client.cpp:72`

**Problem**: `hdl_` is read in `send()` without holding a lock. If `hdl_` is
set during the `open_handler` on a different thread, this is a data race.

**Recommendation**: Protect `hdl_` with `state_mutex_` and set it only in the
`open_handler`.

---

## Summary Scorecard

| Category | Issues | Highest severity |
|----------|--------|-----------------|
| TLS / Security | 2 | CRITICAL |
| Concurrency / Global state | 4 | WARNING |
| RAII / Ownership | 2 | CRITICAL |
| Logging | 2 | WARNING |
| Networking / Reconnect | 1 | WARNING |
| Suggestions | 2 | SUGGESTION |
| **TOTAL** | **13** | **CRITICAL** |

**Overall Risk Rating**: RED — 3 CRITICAL findings present.

---

*Generated by the `cpp-production-engineer` skill.
Re-run `/cpp-production-engineer` after applying fixes.*
