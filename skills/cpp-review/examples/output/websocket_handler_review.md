# C++ Real-Time Code Review

**Date**: 2026-03-12
**Scope**: `examples/input/websocket_handler.cpp`
**Files reviewed**: `websocket_handler.cpp`

> This is the reference example output produced by the `cpp-realtime-reviewer`
> skill for the mock QKD WebSocket handler. It demonstrates the expected report
> structure, severity tagging, inline annotations, and scorecard format.

---

## Findings

---

### [CRITICAL] [D5 / C1] — Session key logged in plaintext

**File**: `websocket_handler.cpp:176–181`

```cpp
// DEFECTIVE — key material written to the log
std::ostringstream oss;
oss << "derive_session_key: peer=" << s->peer_id << " key=";
for (int i = 0; i < 32; ++i)
    oss << std::hex << static_cast<int>(s->session_key[i]);
log_message(3, oss.str());   // ← 256-bit session key printed to stdout
```

**Problem**: The full 256-bit derived session key is formatted into a debug log
message and sent to `stdout`. In a QKD ground-station context this is a
complete key compromise: any process with access to stdout (log aggregator,
container log collector, `journald`, a misconfigured syslog forwarder) will
capture the key. The problem persists even if the log level is reduced —
the `oss` construction still executes and the key is held in a `std::string`
on the heap.

**Fix**: Remove the key from log output entirely. Log only non-sensitive
metadata.

```cpp
// CORRECT — no key material in the log
log_message(3, "derive_session_key: peer=" + s->peer_id + " completed");
```

If key fingerprinting is needed for debugging, log a truncated HMAC over the
key with a known test vector — never the raw key bytes.

---

### [CRITICAL] [D3 / C1] — Session key not zeroed before `Session` is freed

**File**: `websocket_handler.cpp:119–124`

```cpp
void remove_session(int fd) {
    std::lock_guard<std::mutex> lk(g_sessions_mtx);
    auto it = g_sessions.find(fd);
    if (it != g_sessions.end()) {
        // ← session_key[32] NOT zeroed here
        delete it->second;   // key bytes linger in freed heap block
        g_sessions.erase(it);
    }
}
```

**Problem**: The 256-bit `session_key` inside `Session` is never zeroed before
`delete`. The bytes remain accessible in the freed heap block until the
allocator reuses the memory. A heap-spray, use-after-free exploit, or core dump
can recover the key long after the session closes.

**Fix**: Zero sensitive fields before deallocation. Use `OPENSSL_cleanse` (which
the compiler cannot optimise away) rather than `memset`.

```cpp
void remove_session(int fd) {
    std::lock_guard<std::mutex> lk(g_sessions_mtx);
    auto it = g_sessions.find(fd);
    if (it != g_sessions.end()) {
        OPENSSL_cleanse(it->second->session_key, sizeof(it->second->session_key));
        delete it->second;
        g_sessions.erase(it);
    }
}
```

For a more systematic fix, store `session_key` in a custom `SecureBuffer` type
whose destructor calls `OPENSSL_cleanse`.

---

### [CRITICAL] [D1] — Data race on `g_total_bytes_in` / `g_total_bytes_out`

**File**: `websocket_handler.cpp:201`, `websocket_handler.cpp:221`, `websocket_handler.cpp:247–248`

```cpp
// connection_handler (thread N):
g_total_bytes_in += static_cast<uint64_t>(n);   // line 201 — no lock, no atomic

// dispatch_message (called from connection_handler, under g_dispatch_mtx only):
g_total_bytes_in += len;                          // line 221 — different lock scope

// broadcast_key_refresh (called from acceptor/main thread):
g_total_bytes_out += key_len * g_sessions.size(); // line 247 — no lock, no atomic
```

**Problem**: `g_total_bytes_in` and `g_total_bytes_out` are plain `uint64_t`
variables written from multiple threads with no synchronisation. This is a data
race — undefined behaviour per the C++ standard. On 32-bit ARM or MIPS targets,
a 64-bit addition is non-atomic at the machine level, meaning torn reads are
possible even without compiler optimisation. Additionally,
`g_total_bytes_in` is updated both in `connection_handler` (with no lock) and
in `dispatch_message` (under `g_dispatch_mtx`), making the lock discipline
inconsistent.

**Fix**: Replace with `std::atomic<uint64_t>` with `memory_order_relaxed`
(counters do not need ordering guarantees, just atomicity).

```cpp
// Header / global
std::atomic<uint64_t> g_total_bytes_in{0};
std::atomic<uint64_t> g_total_bytes_out{0};

// All update sites
g_total_bytes_in.fetch_add(n, std::memory_order_relaxed);
g_total_bytes_out.fetch_add(key_len * session_count, std::memory_order_relaxed);
```

Remove the redundant update inside `dispatch_message` (only one site should own
the increment per received message).

---

### [CRITICAL] [D1] — `broadcast_key_refresh` iterates `g_sessions` without a lock

**File**: `websocket_handler.cpp:232–249`

```cpp
void broadcast_key_refresh(const uint8_t* new_key, size_t key_len) {
    // ← g_sessions_mtx NOT held
    for (auto& [fd, session] : g_sessions) {   // concurrent modification = UB
        ...
        session->bytes_sent += ...;   // concurrent write to Session member
    }
    g_total_bytes_out += key_len * g_sessions.size();
}
```

**Problem**: `broadcast_key_refresh` reads and iterates `g_sessions` while
`connection_handler` threads may concurrently call `register_session` or
`remove_session` (both of which modify the map under `g_sessions_mtx`).
Concurrent modification of a `std::map` without synchronisation is undefined
behaviour and will crash under load. Additionally, `session->bytes_sent` is
written here and read in `connection_handler` without any synchronisation.

**Fix**: Hold `g_sessions_mtx` for the entire iteration, or build a snapshot
under the lock and iterate the snapshot outside it.

```cpp
void broadcast_key_refresh(const uint8_t* new_key, size_t key_len) {
    // Snapshot under lock — release before doing I/O
    std::vector<std::pair<int, Session*>> snapshot;
    {
        std::lock_guard<std::mutex> lk(g_sessions_mtx);
        snapshot.assign(g_sessions.begin(), g_sessions.end());
    }
    size_t sent_count = 0;
    for (auto& [fd, session] : snapshot) {
        if (session->state == QkdState::AUTHENTICATED) {
            ssize_t written = write(fd, new_key, key_len);
            if (written > 0) {
                // bytes_sent must be atomic or protected by a per-session lock
                session->bytes_sent.fetch_add(written, std::memory_order_relaxed);
                ++sent_count;
            }
        }
    }
    g_total_bytes_out.fetch_add(key_len * sent_count, std::memory_order_relaxed);
}
```

---

### [CRITICAL] [D2] — `g_shutdown` is `volatile bool`, not `std::atomic<bool>`

**File**: `websocket_handler.cpp:50`, `websocket_handler.cpp:211`, `websocket_handler.cpp:262`

```cpp
volatile bool g_shutdown = false;   // line 50

while (!g_shutdown) { ... }         // line 211, line 262
```

**Problem**: `volatile` prevents the compiler from caching the variable in a
register but provides **no memory ordering guarantees** between threads.
The C++ memory model requires `std::atomic` for inter-thread communication.
Using `volatile bool` is a data race (undefined behaviour). Furthermore,
`g_shutdown` is set inside a signal handler (line 276), but it is also read
from normal threads — the combination is unsafe.

**Fix**: Replace with `std::atomic<bool>` and use
`memory_order_relaxed` for the flag (relaxed is sufficient for a simple
shutdown flag that does not need to synchronise other data).

```cpp
std::atomic<bool> g_shutdown{false};   // thread-safe, correct memory model

// In signal handler — but prefer a pipe/eventfd for signal-to-thread
// notification instead of shared memory:
g_shutdown.store(true, std::memory_order_relaxed);
```

---

### [CRITICAL] [D2] — Condition variable wait without predicate — spurious wake-up

**File**: `websocket_handler.cpp:286–287`

```cpp
std::unique_lock<std::mutex> lk(g_stats_cv_mtx);
g_stats_cv.wait(lk);   // ← no predicate; spurious wake-up will proceed early
```

**Problem**: `std::condition_variable::wait` can return spuriously — without
`notify_one` / `notify_all` being called. Without a predicate loop the
`stats_reporter` thread will proceed to print statistics at an arbitrary
time, reading `g_total_bytes_in`, `g_total_bytes_out`, and `g_sessions.size()`
without synchronisation.

**Fix**: Always use the predicate overload (or an explicit `while` loop).

```cpp
std::unique_lock<std::mutex> lk(g_stats_cv_mtx);
g_stats_cv.wait(lk, []{ return g_stats_ready || g_shutdown.load(std::memory_order_relaxed); });
```

---

### [CRITICAL] [D5] — `printf` and `g_stats_cv.notify_all` called from a signal handler

**File**: `websocket_handler.cpp:272–277`

```cpp
void handle_shutdown_signal(int /*signum*/) {
    printf("Shutting down...\n");   // NOT async-signal-safe
    g_shutdown = true;
    g_stats_cv.notify_all();        // NOT async-signal-safe
}
```

**Problem**: `printf` is **not** async-signal-safe (POSIX list of safe
functions does not include it). `std::condition_variable::notify_all`
is also not async-signal-safe — calling it from a signal handler is undefined
behaviour. On Linux with pthreads this can deadlock if the signal interrupts
the thread at a point where it holds an internal lock used by `notify_all`.

**Fix**: Use only async-signal-safe primitives in the signal handler. The
idiomatic approach is to write a byte to a `pipe` or `eventfd` and have the
main loop poll it.

```cpp
// Use a self-pipe or eventfd for signal-to-main-loop notification
static int g_signal_pipe[2];

void handle_shutdown_signal(int /*signum*/) {
    // write() is async-signal-safe; ignoring error intentionally in handler
    char byte = 1;
    (void)write(g_signal_pipe[1], &byte, 1);
}
```

---

### [CRITICAL] [D3] — `EVP_PKEY_CTX` leaked on early error returns in `derive_session_key`

**File**: `websocket_handler.cpp:148–163`

```cpp
EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_HKDF, nullptr);
if (!ctx) return false;

if (EVP_PKEY_derive_init(ctx) <= 0)              return false;  // leaks ctx
if (EVP_PKEY_CTX_set_hkdf_md(ctx, EVP_sha256()) <= 0) return false;  // leaks ctx
```

**Problem**: On the first two error-return paths, `ctx` is not passed to
`EVP_PKEY_CTX_free`. Every failed HKDF initialisation leaks an OpenSSL context
object. On a high-throughput QKD node under adversarial conditions (invalid
handshake flood), this is an unbounded memory leak that will eventually exhaust
the process heap.

**Fix**: Wrap the context in a custom RAII deleter or use C++11 `unique_ptr`
with a custom deleter.

```cpp
struct EvpPkeyCtxDeleter {
    void operator()(EVP_PKEY_CTX* p) const noexcept { EVP_PKEY_CTX_free(p); }
};
using EvpPkeyCtxPtr = std::unique_ptr<EVP_PKEY_CTX, EvpPkeyCtxDeleter>;

bool derive_session_key(Session* s, const uint8_t* ikm, size_t ikm_len) {
    EvpPkeyCtxPtr ctx{EVP_PKEY_CTX_new_id(EVP_PKEY_HKDF, nullptr)};
    if (!ctx) return false;
    if (EVP_PKEY_derive_init(ctx.get()) <= 0) return false;   // ctx freed automatically
    if (EVP_PKEY_CTX_set_hkdf_md(ctx.get(), EVP_sha256()) <= 0) return false;
    // ...
}
```

---

### [WARNING] [D3] — `WsFrame::payload` raw owning pointer; `WsFrame` itself leaked

**File**: `websocket_handler.cpp:95–115` and `websocket_handler.cpp:224–225`

```cpp
// parse_frame allocates both WsFrame* and frame->payload manually
WsFrame* frame = new WsFrame{};
frame->payload = allocate_key_buffer(plen);

// In connection_handler:
free_key_buffer(frame->payload);
// ← delete frame; is MISSING — WsFrame is leaked every iteration
```

**Problem**: `frame->payload` is freed, but the `WsFrame` object itself is
never deleted. Every iteration of the receive loop leaks a `WsFrame` on the
heap. Over time this exhausts memory silently. Additionally, any exception
thrown between `parse_frame` and the manual `free_key_buffer` call will
leak `frame->payload` too.

**Fix**: Replace with RAII ownership.

```cpp
struct WsFrame {
    bool     fin;
    uint8_t  opcode;
    std::vector<uint8_t> payload;   // owns payload, freed automatically
};

std::unique_ptr<WsFrame> parse_frame(const uint8_t* buf, size_t buf_len) {
    auto frame = std::make_unique<WsFrame>();
    // ...
    frame->payload.assign(buf + header_len, buf + header_len + plen);
    return frame;   // ownership transferred to caller
}
```

---

### [WARNING] [D1 / C2] — `g_qrng_seed` accessed from multiple threads without synchronisation

**File**: `websocket_handler.cpp:55–66`

```cpp
uint32_t g_qrng_seed = 0;           // plain, non-atomic

void refresh_qrng_seed(uint32_t new_seed) {
    g_qrng_seed = new_seed;          // non-atomic write
}

uint32_t get_qrng_entropy() {
    return g_qrng_seed ^ 0xDEADBEEF; // non-atomic read
}
```

**Problem**: `g_qrng_seed` is a shared 32-bit variable written by one thread
(presumably a QRNG refresh task) and read by every `connection_handler` thread
during key derivation. This is a data race. In addition, the derived entropy
value (`seed ^ 0xDEADBEEF`) uses only 32 bits of entropy for a 128-bit salt
slot, producing a severely biased salt.

**Fix**: Use `std::atomic<uint32_t>` with `memory_order_acquire` on reads and
`memory_order_release` on writes to ensure any auxiliary state written before
the seed update is visible to readers.

```cpp
std::atomic<uint32_t> g_qrng_seed{0};

void refresh_qrng_seed(uint32_t new_seed) {
    g_qrng_seed.store(new_seed, std::memory_order_release);
}

uint32_t get_qrng_entropy() {
    return g_qrng_seed.load(std::memory_order_acquire) ^ 0xDEADBEEF;
}
```

Also file a separate ticket to fill the full 16-byte salt from the QRNG
source rather than using a 4-byte XOR.

---

### [WARNING] [D4] — Blocking `usleep` inside `dispatch_message` hot path

**File**: `websocket_handler.cpp:218–219`

```cpp
void dispatch_message(Session* s, const uint8_t* payload, size_t len) {
    std::lock_guard<std::mutex> lk(g_dispatch_mtx);
    // ...
    usleep(500);   // ← 500 µs blocking sleep while holding g_dispatch_mtx
```

**Problem**: `usleep(500)` is called while holding `g_dispatch_mtx`. Every
other thread calling `dispatch_message` (one per connected client) blocks for
at least 500 µs waiting to acquire the mutex. With N concurrent sessions this
serialises all message processing and introduces O(N × 500 µs) worst-case
latency on a single dispatch call. On a Linux non-RT kernel, `usleep` can
sleep significantly longer than requested.

**Fix**: Remove the sleep from the hot path. If a real-time delay is needed
for protocol conformance, implement it via a per-session timer outside the
global dispatch lock, or move to an async event loop.

```cpp
void dispatch_message(Session* s, const uint8_t* payload, size_t len) {
    // Process message — keep critical section minimal, no sleeping
    std::vector<uint8_t> copy(payload, payload + len);
    g_total_bytes_in.fetch_add(len, std::memory_order_relaxed);

    // Schedule any timer-based follow-up via a separate timer wheel,
    // not by sleeping inside the lock.
}
```

---

### [WARNING] [D4] — Dynamic allocation per dispatch call inside hot path

**File**: `websocket_handler.cpp:216`

```cpp
// BUG D4: heap allocation on every dispatched message
std::vector<uint8_t> copy(payload, payload + len);
```

**Problem**: Constructing a `std::vector` with `payload..len` performs a heap
allocation on every received message, from within a mutex-protected hot path.
On an embedded QKD node with high key-exchange rates this adds allocator
contention and latency jitter.

**Fix**: If a copy is necessary, use a per-session pre-allocated ring buffer or
a fixed-size stack buffer with a maximum frame size assertion.

```cpp
// For frames bounded to a known max size:
constexpr size_t kMaxPayload = 1500;
static_assert(sizeof(buf) >= kMaxPayload);
uint8_t copy[kMaxPayload];
assert(len <= kMaxPayload);
std::memcpy(copy, payload, len);
```

---

### [WARNING] [D4] — Unbounded `std::thread` creation per connection

**File**: `websocket_handler.cpp:266–268`

```cpp
std::thread t(connection_handler, client_fd);
t.detach();
```

**Problem**: A new OS thread is allocated and immediately detached for every
incoming connection. Thread creation involves dynamic allocation, stack
allocation, and a `clone` syscall. On a real-time satellite-ground link node
with bursty connection attempts (intentional or adversarial) this causes
unbounded thread creation, exhausting the system thread limit and the allocator.
Detached threads are also untrackable — there is no way to join them on
shutdown.

**Fix**: Use a bounded thread pool with a work queue. For a QKD node with a
known maximum number of simultaneous peer connections, the pool size can be
fixed at compile time.

```cpp
// Example: fixed-size thread pool (boost::asio, or a hand-rolled one)
// Each worker thread pulls connection fds from a bounded queue.
// Reject connections when the queue is full (back-pressure).
```

---

### [WARNING] [D4 / D5] — `log_message` called under `g_dispatch_mtx`

**File**: `websocket_handler.cpp:213`

```cpp
void dispatch_message(Session* s, const uint8_t* payload, size_t len) {
    std::lock_guard<std::mutex> lk(g_dispatch_mtx);
    log_message(3, "dispatch: peer=" + s->peer_id);   // ← logging under lock
```

**Problem**: `log_message` calls `std::cout << ... << std::endl` which can
acquire an internal `cout` mutex and flush the stream — both potentially
blocking operations. Calling this while holding `g_dispatch_mtx` extends the
lock hold time with an unbounded I/O delay and risks priority inversion.

**Fix**: Move all log calls outside the lock scope. Build the log string before
or after acquiring the lock.

```cpp
void dispatch_message(Session* s, const uint8_t* payload, size_t len) {
    const std::string peer_id = s->peer_id;  // copy before acquiring lock
    {
        std::lock_guard<std::mutex> lk(g_dispatch_mtx);
        g_total_bytes_in.fetch_add(len, std::memory_order_relaxed);
    }
    // Log outside the lock
    log_message(3, "dispatch: peer=" + peer_id);
}
```

---

### [WARNING] [D5] — Raw frame payload logged on key derivation failure (log injection)

**File**: `websocket_handler.cpp:208–211`

```cpp
log_message(1, "key derivation failed for peer=" + s->peer_id +
               " input=" + std::string(reinterpret_cast<char*>(frame->payload),
                                       frame->payload_len));
```

**Problem**: The raw bytes of the incoming IKM (initial keying material) are
cast to a `std::string` and appended to a log message verbatim. An adversary
sending crafted binary input (containing null bytes, ANSI escape codes, or
log-format injection tokens) can:
1. Corrupt the log stream (log injection).
2. Cause the log message to be interpreted as control sequences by a terminal
   or log viewer.
3. Expose partial key material that the peer sent — useful for cryptanalysis.

**Fix**: Log only the byte length and a safe peer identifier; never log raw
binary input.

```cpp
log_message(1, "key derivation failed: peer=" + s->peer_id +
               " ikm_len=" + std::to_string(frame->payload_len));
```

---

### [SUGGESTION] [D2] — Use `std::scoped_lock` when locking multiple mutexes in `stats_reporter`

**File**: `websocket_handler.cpp:283–295`

**Problem**: The stats reporter locks `g_stats_cv_mtx` via `unique_lock` but
also implicitly relies on `g_sessions_mtx` to be safe when reading
`g_sessions.size()`. If future code adds a second lock acquisition in this
function, `std::scoped_lock` prevents deadlock by acquiring both locks
simultaneously using `std::lock` internally.

**Fix**: Document the lock dependency; use `std::scoped_lock` proactively for
any function acquiring two or more mutexes.

---

### [SUGGESTION] [D3] — Use a zeroing allocator for `session_key`

**File**: `websocket_handler.cpp:33`

```cpp
struct Session {
    // ...
    uint8_t  session_key[32];
```

**Problem**: The key is stored in a plain `uint8_t` array. If `Session` is ever
moved into a `std::vector` (reallocation) the key bytes may be left in the old
buffer without zeroing. Consider a `SecureBuffer<32>` type whose move
constructor zeros the source.

---

### [SUGGESTION] [D4] — Use an async, lock-free logger for the hot path

**File**: `websocket_handler.cpp:70–75`

**Problem**: `log_message` writes to `std::cout` with `std::endl` on every
call. `std::endl` flushes the stream buffer, which may trigger a `write`
syscall. On a high-throughput node this adds measurable latency per frame.

**Fix**: Switch to spdlog in async mode (lock-free SPSC queue to a dedicated
logger thread) or NanoLog, both of which keep the hot-path cost to a
nanosecond-scale enqueue operation.

---

## Summary Scorecard

| Domain | Issues | Highest severity |
|--------|--------|-----------------|
| D1 Thread Safety & Race Conditions | 4 | CRITICAL |
| D2 Synchronisation Primitives | 2 | CRITICAL |
| D3 RAII & Resource Ownership | 3 | CRITICAL |
| D4 Latency & Hot-Path Hygiene | 4 | WARNING |
| D5 Concurrency-Safe Logging | 3 | CRITICAL |
| QKD / Crypto-Specific (C1–C4) | 2 | CRITICAL |
| **TOTAL** | **18** | |

**Overall Risk Rating**: 🔴 HIGH

| Rating | Criteria |
|--------|----------|
| 🔴 HIGH | Any CRITICAL finding present |
| 🟡 MEDIUM | No CRITICAL, but ≥ 1 WARNING |
| 🟢 LOW | Suggestions only |
| ✅ PASS | No findings |

---

## PR / Code-Review Checklist

```
## C++ Real-Time Safety Checklist

### D1 — Thread Safety & Race Conditions
- [ ] All shared state accessed under the correct lock or via std::atomic
- [ ] No TOCTOU patterns (check-then-act on shared state without a lock)
- [ ] Multi-mutex acquisitions use std::scoped_lock or std::lock to prevent deadlock
- [ ] Lock ordering is consistent across all call paths
- [ ] No iterators / pointers cached across unlocked windows

### D2 — Synchronisation Primitives
- [ ] All mutex locks managed via RAII (lock_guard / unique_lock / scoped_lock)
- [ ] Condition variable waits use predicate loop or predicate-overload wait()
- [ ] notify_one / notify_all called after (not before) updating the predicate
- [ ] Atomic memory orders are correct (acquire/release paired, not relaxed where ordering matters)
- [ ] No manual .lock() / .unlock() calls

### D3 — RAII & Resource Ownership
- [ ] No raw new / delete outside low-level allocation classes
- [ ] File descriptors, sockets, and OS handles wrapped in RAII types
- [ ] Crypto contexts (EVP_*, SSL_CTX) freed on all code paths via RAII
- [ ] No shared_ptr cycles; weak_ptr used where back-references are needed
- [ ] Cryptographic key buffers zeroed before deallocation (memset_s / OPENSSL_cleanse)

### D4 — Latency & Hot-Path Hygiene
- [ ] No dynamic allocation (new, push_back with realloc) in real-time paths
- [ ] No blocking syscalls (sleep, blocking recv, fflush) in packet/frame handlers
- [ ] Mutex critical sections are minimal (no I/O or long computation inside a lock)
- [ ] Per-thread hot data padded to hardware_destructive_interference_size
- [ ] Pre-allocated / pre-reserved containers used in hot loops

### D5 — Concurrency-Safe Logging
- [ ] Logging library is thread-safe (or calls are serialised)
- [ ] No synchronous flushing log calls (std::endl, fflush) in real-time loops
- [ ] Log calls are outside mutex critical sections
- [ ] No key material, QRNG seeds, or authentication tokens in log messages
- [ ] Format strings are string literals (not user-controlled)

### QKD / Crypto-Specific
- [ ] Key material zeroed immediately after use
- [ ] QRNG seed / entropy source access is synchronised
- [ ] QKD state machine transitions are atomic w.r.t. concurrent observers
- [ ] Secret-dependent comparisons use constant-time primitives
- [ ] No timing side-channels on secret-dependent branches

### Sign-off
- [ ] All CRITICAL findings resolved or have a tracked remediation ticket
- [ ] All WARNING findings resolved or accepted with written justification
- [ ] Reviewer confirms the above checklist was worked through
```

---

*Generated by the `cpp-realtime-reviewer` skill.
Re-run `/cpp-realtime-reviewer <path>` after significant concurrency or
real-time changes.*
