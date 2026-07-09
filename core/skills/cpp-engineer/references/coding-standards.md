# C++ Production Engineering Coding Standards

Reference document for the `cpp-production-engineer` skill.
Apply every rule in this document unconditionally. Deviations require an
explicit written justification.

---

## 1. Language Standard

- **Default**: C++17. Every target sets `cxx_std_17` via `target_compile_features`.
- **C++20+ features**: Allowed only with an explicit `SUGGESTION` annotation
  and a note that the standard must be raised. Never use silently.
- **Extensions**: Always set `CXX_EXTENSIONS OFF` to prevent GCC/Clang
  non-standard extensions from silently compiling.

---

## 2. Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Classes / structs | `PascalCase` | `KeyManager`, `WsClient` |
| Member variables | `snake_case_` (trailing underscore) | `mutex_`, `level_` |
| Local variables | `snake_case` | `snapshot`, `endpoint` |
| Constants / `constexpr` | `kPascalCase` | `kMaxRetries` |
| Enum members | `PascalCase` | `ConnState::Connected` |
| Free functions | `snake_case` | `parse_frame()` |
| Template parameters | `PascalCase` | `template <typename T>` |
| Files | `snake_case.cpp` / `snake_case.hpp` | `key_manager.cpp` |

---

## 3. Concurrency Rules

### Mutex documentation
Every `std::mutex` must be annotated with a comment listing the fields it
protects:

```cpp
// Protects: data_, state_
mutable std::mutex mutex_;
```

### Lock scope
- `std::lock_guard<std::mutex>` — simple, non-transferable scopes.
- `std::unique_lock<std::mutex>` — when early release or `condition_variable`
  is needed.
- `std::scoped_lock` (C++17) — when two or more mutexes must be locked
  simultaneously (deadlock prevention).
- **Never** hold a mutex across I/O, WebSocket sends, or any potentially
  blocking call. Copy data under the lock; perform I/O outside.

### Singletons
Use Meyers singleton (local static). Thread-safe by C++11/17 standard.
Mutable operations on the singleton must hold the instance mutex.

### Thread lifecycle
- Always join or detach before the owning object is destroyed.
- Use a `stop_` flag + `std::condition_variable` to signal worker threads.
- Destructor must be `noexcept`; catch-and-log any cleanup exceptions inside
  the destructor body.

---

## 4. Resource Management (RAII)

| Rule | Severity if violated |
|------|---------------------|
| No raw owning pointers. Every heap allocation owned by a smart pointer from construction. | CRITICAL |
| Use `std::make_unique` / `std::make_shared`. Never pair bare `new` with a smart pointer constructor. | CRITICAL |
| Destructors must be `noexcept`. If cleanup can throw, catch and log inside the destructor. | CRITICAL |
| C library handles (FDs, SSL contexts) wrapped in a thin RAII deleter struct. | WARNING |
| `std::unique_ptr` for sole ownership. `std::shared_ptr` only when shared ownership is genuinely required (document why). | WARNING |

---

## 5. Logging Standards

### Required fields (in order)
1. ISO 8601 timestamp with millisecond precision
2. Severity (`EMERG`, `ALERT`, `CRIT`, `ERR`, `WARNING`, `NOTICE`, `INFO`, `DEBUG`)
3. Facility (`LOCAL0`–`LOCAL7` per component convention)
4. Component name (e.g. `GARBO.KeyManager`, `QMO.WsClient`)
5. Thread ID (`std::this_thread::get_id()`)
6. Message

### Key material rule — CRITICAL
**Never** log:
- Raw key bytes or key material in any form
- Session tokens or authentication credentials
- Private key material or PRNG seeds
- Key identifiers that could be correlated with the key value

A non-secret key UUID/label for tracing is acceptable; the key value is not.

### Production paths
Use `openlog`/`syslog`/`closelog` (or a wrapper delegating to them) in daemon
processes. Never write to `std::cout`/`std::cerr` in production paths.

### Severity configurable at runtime
Active log level must be configurable via config file or environment variable
without recompilation.

---

## 6. Networking (websocketpp + Boost.Asio)

### TLS — mandatory
```cpp
// Minimum required TLS configuration
auto ctx = std::make_shared<boost::asio::ssl::context>(
    boost::asio::ssl::context::tlsv12_client);
ctx->set_verify_mode(boost::asio::ssl::verify_peer);
ctx->load_verify_file(ca_bundle_path_);
// NEVER: ctx->set_verify_mode(boost::asio::ssl::verify_none)
```

### Reconnect state machine
```cpp
enum class ConnState { Disconnected, Connecting, Connected, Reconnecting };
// Protect state transitions with a mutex.
// Log every reconnect attempt at WARNING.
// Exponential back-off: start 1s, max 60s, jitter ±10%.
```

### Reconnect checklist (mandatory before accepting any networking code)
- What happens on reconnect? (subscriptions, pending sends, sequence numbers)
- What happens if the remote dies mid-message? (partial buffer, logging, clean close)

### Partial frame buffering
Maintain a per-connection receive buffer. Parse only on complete logical record
delimiters. Guard the buffer with its connection's mutex.

---

## 7. CMake Rules

| Rule | Severity |
|------|---------|
| No `file(GLOB ...)` for source lists. List every `.cpp` explicitly. | WARNING |
| Library headers via `target_include_directories(... PUBLIC include/)`, never `include_directories()`. | WARNING |
| `target_link_libraries` with explicit `PUBLIC`/`PRIVATE`/`INTERFACE`. Never raw `link_libraries()`. | WARNING |
| `target_compile_options(<target> PRIVATE -Wall -Wextra -Werror)` on every target in CI. | WARNING |
| `find_package` must specify a minimum version. | WARNING |
| `FetchContent` must pin a tag or commit hash. | WARNING |
| Unit test target (`ctest`/`add_test`) must be present and build cleanly. | WARNING |

---

## 8. Testing Standards

| Rule | Note |
|------|------|
| Test file naming: `<ClassName>Test.cpp` or `<module>_test.cpp` | |
| `TEST_F` with fixture for stateful components; `TEST` for pure functions | |
| Mock external dependencies (network, filesystem, time) with `gmock` | Never make real network calls in unit tests |
| Tests must be deterministic — no `sleep`, no wall-clock assertions | Use dependency injection to control time |
| Descriptive test names: `LogManager_SetLevel_FiltersBelowThreshold` | Not `Test1` |
| Each test independent — no shared global state between tests | Use `SetUp()`/`TearDown()` for isolation |

---

## 9. CI/CD Rules

### Jenkinsfile stage order
`Checkout → Build → Test → Static Analysis → Archive`

### SonarQube
- Blocker severity issues **fail the build** (`waitForQualityGate(abortPipeline: true)`)
- Critical severity issues are minimum WARNING findings
- Never suppress or ignore a Blocker finding — resolve it

### Git flow
- `feature/*` → feature work
- `bugfix/*` → bug fixes
- `release/*` → release preparation
- **No direct pushes to `master`** — CRITICAL process violation
- All merges via pull request with ≥1 reviewer approval + passing Jenkins build

---

## 10. Severity Classification

| Severity | When to use |
|----------|-------------|
| **CRITICAL** | Directly enables a security breach, data loss, crash, or undefined behaviour; violates a hard rule above |
| **WARNING** | Weakens correctness, maintainability, or security posture; violates a coding standard |
| **SUGGESTION** | Defensive improvement or alignment with convention; current code is not actively harmful |
