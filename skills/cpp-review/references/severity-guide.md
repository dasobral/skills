# Severity Classification Guide

Rules for assigning **CRITICAL**, **WARNING**, or **SUGGESTION** tags to
findings produced by the `cpp-realtime-reviewer` skill.

Apply these rules consistently. When a finding could be classified at multiple
levels, choose the highest applicable level.

---

## CRITICAL

A finding is CRITICAL when it meets **one or more** of the following criteria:

### Undefined behaviour
- The code triggers C++ undefined behaviour (data race, signed integer
  overflow used as an invariant, out-of-bounds access, use-after-free,
  double-free, null dereference in production code).
- A `reinterpret_cast` or `memcpy` breaks the strict-aliasing rule on a
  type that is not `char` / `unsigned char` / `std::byte`.

### Data corruption or silent data loss
- A race condition that can silently corrupt shared state (e.g., two threads
  writing a non-atomic 64-bit value on a 32-bit bus without a lock).
- A missed condition-variable notification that causes a consumer thread to
  stall permanently (deadlock by omission).

### Deadlock
- A lock-ordering inversion that can deadlock two or more threads.
- Locking a non-recursive mutex twice on the same thread.
- Holding a lock while calling a callback or virtual function that may attempt
  to acquire the same lock.

### Cryptographic key / secret exposure
- Any path that writes key material, QRNG seeds, authentication tokens, or
  session secrets to a log, stdout/stderr, a plain-text file, or an
  unencrypted network socket.
- Key material not zeroed before deallocation (leaves secrets accessible in
  freed memory or core dumps).
- Timing side-channel on a secret-dependent branch where a constant-time
  primitive exists.

### Hard real-time violation with safety consequence
- A blocking call (unbounded wait, blocking I/O, dynamic allocation) inside
  an ISR, a hard-deadline interrupt handler, or a path explicitly marked as
  time-critical in the system spec.

### Memory unsafety
- Use of a freed object, dangling pointer dereference, or buffer overrun that
  can corrupt adjacent memory.
- A `std::shared_ptr` cycle that leaks large or security-sensitive objects
  indefinitely.

---

## WARNING

A finding is WARNING when it meets **one or more** of the following criteria
and does not already qualify as CRITICAL:

### Likely bug under normal operation
- A spurious wake-up in a condition variable wait that is not protected by a
  predicate loop — causes the consumer to proceed with invalid state.
- A `compare_exchange_weak` without a retry loop — silently drops updates.
- An atomic load-then-use pattern where the value may change between the load
  and the use, producing logically inconsistent behaviour.
- `volatile` used as a substitute for `std::atomic` for inter-thread
  communication — does not provide the required memory ordering.

### Unsafe in concurrency but not immediately UB
- A container iterated without a lock while another thread may modify it
  (invalidates iterators; likely crash under load even if technically UB).
- `printf` / `std::cout` called concurrently without synchronisation —
  output garbled; on some platforms, a data race on the FILE* lock.
- Manual `.lock()` / `.unlock()` without RAII — will leak the lock if an
  exception is thrown.

### Latency violation in soft-real-time or throughput-critical path
- A blocking syscall or synchronous log flush inside a packet-processing loop
  or frame handler that has a throughput requirement.
- Dynamic allocation (`new`, `push_back` with realloc) inside a hot loop
  where a pre-allocated pool or fixed-size container should be used.
- A mutex held across a long-running operation (file read, DNS lookup,
  external RPC) that blocks unrelated threads.

### Cryptographic weakness without direct key exposure
- Entropy / QRNG output used before sufficient initial accumulation.
- Fallback to a weaker random source without logging or alerting.
- Secret-dependent comparison using `memcmp` instead of a constant-time
  function — timing side-channel risk.

### RAII correctness issue with likely resource leak
- A raw handle or file descriptor that is not wrapped in RAII and may leak on
  an exception or non-trivial control-flow path.
- A `std::unique_ptr` reset or release with the raw pointer stored in a
  non-RAII variable.

### Missing synchronisation with low-probability race
- A pattern that is technically a data race but is unlikely to manifest
  outside heavy load (e.g., a flag written once at startup without a memory
  fence, read repeatedly thereafter).

---

## SUGGESTION

A finding is SUGGESTION when it represents a better practice that reduces
risk or improves maintainability but poses no immediate correctness threat:

### Preferred idioms
- Using `std::scoped_lock` instead of multiple sequential `std::lock_guard`
  acquisitions when locking two mutexes simultaneously.
- Using `std::make_unique` / `std::make_shared` instead of `new` inside a
  smart-pointer constructor.
- Using `std::atomic_ref` on an existing plain variable rather than changing
  its type to `std::atomic<T>` in a hot-path context.
- Preferring `std::shared_mutex` over `std::mutex` for read-heavy workloads.

### Defensive coding
- Adding a `static_assert` or `alignas` annotation for cache-line separation
  on per-thread data to prevent false sharing.
- Pre-reserving STL containers before entering a loop to avoid reallocations
  (no immediate latency issue, but prevents future regression).
- Wrapping a raw C crypto API handle in a C++ RAII class even when the current
  code always calls the cleanup correctly.

### Logging improvements
- Gating expensive log message construction behind a level check.
- Switching from synchronous to async logging (spdlog async, NanoLog) to
  reduce log call latency on hot paths.
- Redacting or masking fields that could accidentally contain sensitive data
  in future.

### Code clarity / reviewability
- Adding a comment explaining a non-obvious memory ordering choice.
- Naming a lambda or helper to make the locking invariant explicit.
- Using `[[nodiscard]]` on functions that return error codes that callers
  frequently ignore.

---

## Quick reference table

| Situation | Level |
|-----------|-------|
| Data race (UB per C++ standard) | CRITICAL |
| Deadlock (lock order inversion, recursive non-recursive mutex) | CRITICAL |
| Key / secret written to log or plain-text channel | CRITICAL |
| Key material not zeroed on free | CRITICAL |
| Blocking call in hard-RT ISR | CRITICAL |
| Buffer overrun / use-after-free | CRITICAL |
| Spurious wake-up without predicate guard | WARNING |
| `volatile` as atomic substitute | WARNING |
| `printf` on multiple threads without sync | WARNING |
| Manual lock/unlock without RAII | WARNING |
| Blocking syscall in soft-RT hot path | WARNING |
| Dynamic alloc in hot path | WARNING |
| Missing constant-time comparison | WARNING |
| Resource leak via non-RAII handle | WARNING |
| Use `scoped_lock` for multi-mutex | SUGGESTION |
| Use `make_unique` / `make_shared` | SUGGESTION |
| Add level check before log construction | SUGGESTION |
| Switch to async logger | SUGGESTION |
| Pre-reserve containers | SUGGESTION |
| Align per-thread data to cache line | SUGGESTION |
