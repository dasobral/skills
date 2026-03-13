# C++ Real-Time Review Checklist

Full per-domain defect checklist for the `cpp-realtime-reviewer` skill.
Work through every item in each domain. For each finding, record the severity,
the affected lines, the defect description, and the fix.

Target audience: senior C++ engineers on cryptographic, QKD/QRNG, and
satellite-ground secure-communication systems.

---

## D1 — Thread Safety & Race Conditions

### 1.1 Unsynchronised shared-state access
- Is every shared data member accessed under the appropriate lock or via an
  atomic?
- Are reads as well as writes synchronised? (Read-without-lock on a mutable
  shared value is a data race even if writes are locked.)
- Are there any `static` local variables in functions called from multiple
  threads? (`static` initialisation is thread-safe since C++11, but mutable
  `static` state is a hidden race.)
- Are global variables mutated from multiple threads without synchronisation?

### 1.2 TOCTOU (Time-Of-Check / Time-Of-Use)
- Is the result of a `load()` on an atomic stored in a local, then used in a
  subsequent branch that relies on the value still being valid?
- Is a file, socket, or OS resource checked for existence then used, without
  holding a lock that prevents interleaved modification?
- Are container `.size()` / `.empty()` results used after releasing a lock?

### 1.3 Lock ordering and deadlock
- Are there multiple mutexes acquired in the same function or call chain?
  Is the acquisition order consistent across all code paths?
- Are any locks acquired inside a callback, lambda, or virtual dispatch where
  the caller already holds a lock (inversion risk)?
- Is `std::lock` / `std::scoped_lock` (variadic) used when two or more mutexes
  must be locked simultaneously?
- Are any recursive lock attempts on a non-recursive mutex?

### 1.4 Iterator / container invalidation under concurrency
- Is a container (vector, map, unordered_map, deque) modified while another
  thread may be iterating it?
- Are iterators or pointers into a container cached across a point where the
  container could be modified?

### 1.5 Signal handlers and interrupt service routines (ISRs)
- Are non-signal-safe functions (`malloc`, `printf`, C++ exceptions) called
  from a signal handler?
- Are shared variables modified from both an ISR and a normal thread without
  `volatile` + appropriate atomic/barrier semantics?
- Is `sig_atomic_t` or `std::atomic<>` used for variables shared between
  signal handlers and the main program?

### 1.6 Memory ordering
- Are relaxed (`memory_order_relaxed`) atomics used on variables that must
  participate in a happens-before relationship?
- Is `compare_exchange_weak` used without a retry loop?
- Is `compare_exchange_strong` used in a tight loop (should be `_weak`)?
- Are acquire/release pairs matched correctly across producer-consumer paths?

---

## D2 — Synchronisation Primitives

### 2.1 Mutex usage
- Is `std::mutex` locked via RAII (`std::lock_guard`, `std::unique_lock`,
  `std::scoped_lock`)? Never call `.lock()` / `.unlock()` manually.
- Are mutexes unlocked before any `return`, `throw`, or `continue` statement
  on every code path? (Symptom of not using RAII.)
- Is a mutex locked twice on the same thread without `std::recursive_mutex`?
  (Deadlock if non-recursive.)
- Is a mutex locked in a destructor that may be called while another thread
  holds the same mutex?
- Is mutex ownership transferred across threads (locked in one thread,
  unlocked in another)? This is undefined behaviour for `std::mutex`.

### 2.2 Condition variables
- Is the wait always inside a `while` loop (or uses the predicate overload of
  `wait`) to guard against spurious wake-ups?
  ```cpp
  // WRONG — spurious wake-up not handled:
  cv.wait(lk);
  // CORRECT:
  cv.wait(lk, [&]{ return ready; });
  ```
- Is the predicate checked while holding the mutex? (Predicate must be
  evaluated inside the lock to avoid a missed-notification race.)
- Is `notify_one` / `notify_all` called after updating the predicate variable,
  not before?
- Is the mutex released between `notify_*` and the wait, or held throughout?
  (Releasing before notify is preferred to avoid the notified thread blocking
  immediately on reacquisition.)
- Is the condition variable used with the correct mutex? (Each `cv.wait` must
  pass the same mutex that protects the predicate.)

### 2.3 Atomics
- Is `std::atomic<bool>` or `std::atomic_flag` used for flags, not plain
  `volatile bool`?
- Are compound operations (read-modify-write) expressed as atomic fetch-add,
  exchange, or compare-exchange rather than a plain load + store pair?
- Is `memory_order_seq_cst` used where relaxed or acq/rel would suffice
  (performance)? Conversely, is relaxed ordering used where sequential
  consistency is required (correctness)?
- Are `std::atomic<T>` objects ever copied? (`std::atomic` is not copyable;
  copying the underlying `T` without synchronisation is a race.)

### 2.4 Reader-writer locks
- When reads vastly outnumber writes, is `std::shared_mutex` (C++17) used
  instead of an exclusive mutex?
- Are write locks (`std::unique_lock<std::shared_mutex>`) held for the minimum
  duration?
- Is there a risk of writer starvation (many continuous readers blocking
  writes)?

### 2.5 Semaphores and counting primitives (C++20 / POSIX)
- Is `std::counting_semaphore` / `std::binary_semaphore` used correctly
  (acquire before use, release after)?
- Is a POSIX `sem_t` checked for errors after `sem_wait` / `sem_post`?

---

## D3 — RAII & Resource Ownership

### 3.1 Raw memory management
- Are there any calls to `new` / `delete` or `new[]` / `delete[]` outside of
  a well-justified low-level allocation class?
- Are there any calls to `malloc` / `free` / `realloc` mixed with C++ objects?
- Are `std::unique_ptr` or `std::shared_ptr` used for heap-allocated objects?
- Is `std::make_unique` / `std::make_shared` used instead of `new` inside a
  smart-pointer constructor?

### 3.2 Ownership semantics
- Is every heap-allocated resource owned by exactly one entity at all times?
- Are raw pointers used for non-owning observation only (never for ownership)?
- Is `std::shared_ptr` used where `std::unique_ptr` would suffice (unnecessary
  reference-count overhead)?
- Are circular `std::shared_ptr` chains present? (Memory leak.)
- Are `std::weak_ptr` handles checked before use (`lock()` returns non-null)?

### 3.3 File, socket, and OS handles
- Are file descriptors, socket handles, `HANDLE` values, and similar OS
  resources wrapped in RAII types?
- Is there any code path where a handle could be leaked on an exception or
  early return?
- Are crypto contexts (OpenSSL `EVP_CIPHER_CTX`, `SSL_CTX`, etc.) wrapped in
  RAII deleters or freed on all code paths?

### 3.4 Exception safety
- Does every constructor that acquires a resource also release it in its
  destructor (or delegate to RAII members)?
- Are there any two-phase constructions (`init()` method separate from
  constructor) where the destructor might run before `init()` completes?
- Is the strong or basic exception-safety guarantee provided for container
  operations?

### 3.5 Cryptographic material
- Are cryptographic keys, seeds, and nonces stored in `std::vector<uint8_t>`
  or plain arrays rather than a zeroing container?
- Is sensitive memory explicitly zeroed before deallocation?
  (`memset_s`, `OPENSSL_cleanse`, or custom secure allocator.)
- Are key buffers passed by raw pointer with no lifetime guarantee?

---

## D4 — Latency & Hot-Path Hygiene

### 4.1 Dynamic memory allocation in hot paths
- Are `new` / `delete`, `std::vector::push_back` (with reallocation),
  `std::string` construction, or other heap operations called on a path that
  must meet a hard deadline?
- Are STL containers pre-sized / pre-reserved before entering the real-time
  loop?
- Are `std::function`, `std::any`, or type-erased wrappers used in hot paths?
  (These often heap-allocate.)

### 4.2 Blocking syscalls
- Are any of the following called on a real-time thread or in a packet/frame
  processing loop without explicit justification?
  - `sleep`, `usleep`, `nanosleep`, `std::this_thread::sleep_for`
  - Blocking `read` / `write` / `recv` / `send` on a socket
  - `fopen` / `fread` / `fwrite` (buffered I/O)
  - `printf` / `fprintf` / `std::cout` (may lock, may allocate)
  - `syslog` / `openlog`
  - `getenv` / `setenv` (not async-signal-safe)
  - `gethostbyname` / `getaddrinfo` (DNS; may block indefinitely)
  - Mutex `.lock()` on a non-try path (unbounded wait)

### 4.3 Lock contention
- Is a mutex held while performing I/O, syscalls, or long computations?
- Is the critical section minimised to the smallest possible scope?
- Are reader threads blocked on an exclusive lock when a shared lock would
  suffice?
- Is a mutex acquired on a hot path that is called thousands of times per
  second? Consider lock-free or wait-free alternatives.

### 4.4 Interrupt Service Routine safety
- Are any non-reentrant or blocking functions called from an ISR?
- Is stack usage inside the ISR bounded and known at compile time?
- Are all ISR-shared variables declared `volatile` AND accessed via atomics or
  with appropriate memory barriers?

### 4.5 Memory layout and cache effects
- Are hot data structures laid out for cache locality (SoA vs. AoS)?
- Are false-sharing hazards present? (Two threads writing to variables on the
  same cache line.)
- Is `alignas(std::hardware_destructive_interference_size)` used to pad
  per-thread data?

### 4.6 Real-time scheduling
- Are threads that must meet deadlines configured with `SCHED_FIFO` or
  `SCHED_RR`?
- Is thread priority inversion possible (high-priority thread waiting on a
  mutex held by a low-priority thread)?
- Is priority inheritance enabled on the relevant mutex
  (`pthread_mutexattr_setprotocol(PTHREAD_PRIO_INHERIT)`)?

---

## D5 — Concurrency-Safe Logging

### 5.1 Unsynchronised logging calls
- Is `printf` / `std::cout` / `std::cerr` called from multiple threads without
  synchronisation? (Interleaved output; potential data race on `FILE*`.)
- Is the logging library used thread-safe? (spdlog, glog, and log4cplus are;
  naive custom loggers often are not.)
- Are log messages assembled from multiple un-guarded writes to a shared
  buffer?

### 5.2 Blocking log calls in hot paths
- Is a synchronous, flushing log call (`std::endl`, `fflush`, `fsync`) made
  inside a real-time loop or packet handler?
- Is a mutex-protected logger called on every packet? Consider an async/lock-
  free ring-buffer logger (spdlog async mode, NanoLog, etc.).
- Are log calls inside a lock's critical section? (Extends lock hold time;
  can cause priority inversion.)

### 5.3 Sensitive data in logs
- Are cryptographic keys, QRNG seeds, authentication tokens, or session
  secrets ever formatted into a log message?
- Are raw byte buffers (containing potential key material) logged with `%s`
  or hex dump helpers without explicit redaction?
- Is there a log-level check before constructing an expensive or sensitive log
  message? (`if (logger->should_log(level)) { ... }`)

### 5.4 Log format safety
- Are format strings for `printf`-family functions string literals, not
  user-controlled or runtime-assembled strings?
- Are `%n` format specifiers present? (Security hazard.)
- Does the structured logging library correctly escape special characters to
  prevent log injection?

### 5.5 Log-related resource management
- Are log file handles, sockets, or buffers owned via RAII?
- Is there a log-rotation or size-cap policy to prevent disk exhaustion on an
  embedded target?
- Are async log queues bounded to prevent unbounded memory growth under high
  load?

---

## QKD / QRNG / Cryptography-Specific Checks

These checks supplement the five domains for the primary target domain.

### C1 — Key material lifetime
- Is key material zeroed immediately after use?
- Are key buffers passed by value (copied) where a reference or pointer suffices
  (unnecessary copies in memory)?
- Is key material ever serialised to a log, file, or network socket without
  encryption?

### C2 — QRNG seeding and entropy
- Is the QRNG seed / entropy source read under appropriate synchronisation if
  shared between threads?
- Is there a fallback path if the QRNG source is unavailable, and is that path
  cryptographically safe?
- Is entropy used before sufficient initial accumulation (seeding starvation)?

### C3 — QKD protocol state machine
- Is the QKD state machine accessed from multiple threads without locking?
- Are state transitions atomic with respect to concurrent observers?
- Is there a timeout on waiting for the remote peer, and is that timeout
  handled safely?

### C4 — Timing side-channels
- Are secret-dependent branches or loops present where constant-time
  equivalents exist (`CRYPTO_memcmp` vs. `memcmp`, constant-time byte
  selection)?
- Are sensitive variables declared `volatile` to prevent compiler
  optimisation that could collapse secret-dependent code?
