# Code Quality Review Checklist

Full per-pillar defect checklist for the `code-quality-reviewer` skill.
Work through every item in each pillar. For each finding, record the severity,
the affected lines, the defect description, and the fix.

Target audience: experienced engineers seeking a second opinion on code health,
not functional correctness.

---

## P1 — Clarity

### 1.1 Naming conventions
- Do variable, function, class, and module names clearly communicate their
  intent? A name should answer "what" without requiring the reader to trace
  the implementation.
- Are abbreviations or single-letter names used outside of conventional
  short scopes (loop counters `i`, `j`; math variables `x`, `y`)?
- Are names consistent with the language's idiomatic conventions
  (e.g. `snake_case` for Python, `camelCase` for JavaScript, `PascalCase`
  for classes)?
- Are boolean variables and functions named to read as predicates
  (`is_valid`, `has_permission`, `can_retry`) rather than nouns or verbs
  (`status`, `check`)?
- Are function names verb-based and descriptive of the action performed
  (`fetch_user_by_id` rather than `user` or `get`)?
- Are names that shadow built-ins, stdlib names, or outer-scope variables
  present?
- Are "generic" names like `data`, `info`, `manager`, `handler`, `util`,
  or `helper` used without meaningful qualification?

### 1.2 Code structure and organisation
- Are functions and methods short enough to fit on one screen (roughly
  ≤ 40 lines) and do they do one thing?
- Is there excessive horizontal nesting (≥ 4 levels of indentation)? Deep
  nesting is often a sign of missing early returns or helper functions.
- Are long parameter lists (≥ 5 positional parameters) present that should
  be grouped into a data object or struct?
- Are magic numbers or magic strings used inline rather than named constants?
- Are related values scattered rather than grouped into enumerations,
  constants modules, or data classes?
- Are there commented-out blocks of dead code that should be removed?
- Is there unreachable code after a `return`, `throw`, `break`, or `continue`?

### 1.3 Comments and documentation
- Do comments explain *why* rather than restating *what* the code does?
  ("Retry up to 3 times because the external API is flaky" is useful;
  "Loop three times" is not.)
- Are there TODOs or FIXMEs with no associated ticket or owner?
- Are public APIs (exported functions, class constructors, REST endpoints)
  documented with their contract: parameters, return value, side effects,
  and error conditions?
- Are there misleading comments that no longer match the code they describe?

### 1.4 Readability patterns
- Are complex boolean expressions broken into named intermediate variables
  or helper predicates?
- Are long method chains used where intermediate variables with meaningful
  names would improve legibility?
- Is code formatted consistently with the project's formatter / linter
  settings? (Flag only when the inconsistency is significant — not micro-
  style nits the formatter should handle.)

---

## P2 — Simplicity

### 2.1 Unnecessary complexity
- Are there loops, conditionals, or data transformations that can be
  replaced by a standard library function?
- Is there custom serialization, caching, or retry logic reimplementing
  what a well-known library already provides correctly?
- Are there multi-level indirection chains (interface → abstract class →
  concrete class → adapter) for a single implementation that will never
  vary?
- Is there a factory, builder, or registry pattern applied to a type
  hierarchy with only one concrete type?

### 2.2 Premature abstraction
- Are there generic type parameters, callbacks, or strategy objects
  introduced for flexibility that is not yet required?
- Are functions or classes parameterised with flags (`mode`, `type`,
  `strategy`) that alter their fundamental behaviour — effectively
  making them two different functions in one?
- Is there an abstraction layer whose only consumer is the layer directly
  above it?
- Are there interfaces or protocols with a single implementation and no
  plans for additional implementations?

### 2.3 Over-engineering
- Is there configuration infrastructure (feature flags, plugin systems,
  dependency injection containers) for a codebase that does not need it?
- Are there custom data structures (linked lists, tries, bloom filters)
  solving problems adequately handled by the language's built-in
  collections?
- Is there speculative code written for hypothetical future requirements
  not described in any ticket or design document?
- Are there more than two levels of inheritance for behaviour that
  composition would handle more clearly?

### 2.4 YAGNI violations
- Is there code, configuration, or infrastructure that is not used by any
  current feature or test?
- Are there exported / public APIs with no external callers?
- Are there environment-specific code paths (staging, canary, debug)
  that are never exercised and not part of active development?

### 2.5 Duplication (DRY)
- Is the same logic copy-pasted in two or more places? (Three or more
  identical or near-identical blocks strongly warrant extraction.)
- Are there parallel data structures (e.g. two arrays that must stay in
  sync by index) that should be a single array of structs?
- Are there repeated conditionals (e.g. the same `if x is None` guard
  duplicated across every call site) that could be encapsulated once?

---

## P3 — Good Practices

### 3.1 SOLID principles
- **Single Responsibility**: Does each class / module have one reason to
  change? God classes (> ~200 lines doing unrelated things) or modules
  mixing IO, business logic, and presentation are violations.
- **Open/Closed**: Is existing behaviour modified directly rather than
  extended? Watch for large `if/elif` chains or `switch` statements
  dispatching on type tags that would grow with each new type.
- **Liskov Substitution**: Do subclasses honour the contract of their
  parent? Methods that throw "not implemented" or silently ignore
  parameters in subclasses are violations.
- **Interface Segregation**: Are clients forced to depend on methods they
  do not use? Wide interfaces (> 7–8 methods) imposed on all implementers
  are a smell.
- **Dependency Inversion**: Do high-level modules depend on concrete
  low-level implementations rather than abstractions? Watch for `new
  ConcreteService()` inside business logic classes.

### 3.2 DRY (Don't Repeat Yourself)
- Is shared business logic centralised, or are variants of the same rule
  spread across multiple modules?
- Are schema validations duplicated between the API layer, the service
  layer, and the database model?

### 3.3 KISS (Keep It Simple, Stupid)
- Is the simplest solution that passes all current requirements used, or
  is complexity added speculatively?
- Are there design patterns (visitor, decorator, chain of responsibility)
  applied where a plain function would be clearer?

### 3.4 Error handling
- Are errors silently swallowed (bare `except: pass`, unchecked return
  values, ignored Promise rejections)?
- Are error messages actionable? ("Connection refused to db:5432 after
  3 retries" is actionable; "Error" is not.)
- Are exceptions used for flow control (raised and caught within the same
  function as a glorified `goto`)?
- Are specific exception types caught where a broad catch would mask
  unexpected errors (`except Exception` / `catch (Exception e)` without
  re-raising or at least logging the full stack trace)?
- Are errors propagated to callers who need them, or are they converted to
  `null` / `undefined` / `-1` silently?
- In async code: are rejected Promises / unhandled goroutine errors /
  unjoined error channels handled?

### 3.5 Testability
- Are there hidden dependencies (global singletons, direct filesystem
  access, system clock reads, network calls) inside business logic that
  make unit testing impossible without monkey-patching?
- Are functions pure (same input → same output, no side effects) where
  they could be? Side-effecting functions are harder to test.
- Is dependency injection (constructor injection, parameter injection)
  used for external collaborators so tests can substitute fakes?
- Are there functions that combine multiple responsibilities, making it
  impossible to test one without triggering the other?
- Are there circular imports / circular dependencies between modules that
  complicate test isolation?

### 3.6 Logging and observability
- Is there sufficient logging at key decision points (request received,
  external call attempted, retry triggered, error encountered)?
- Are log levels used appropriately (`DEBUG` for trace detail, `INFO` for
  operational milestones, `WARNING` for recoverable anomalies, `ERROR` for
  failures)?
- Is structured logging (JSON, key=value) used in services, or is there
  free-form string concatenation that is hard to query?

---

## P4 — Security

### 4.1 Injection vulnerabilities
- Are user-supplied inputs ever interpolated directly into SQL queries,
  shell commands, LDAP filters, XPath expressions, or NoSQL queries?
  (`f"SELECT * FROM users WHERE id = {user_id}"` is SQL injection.)
- Are parameterised queries / prepared statements used for all database
  interactions?
- Is `subprocess` / `child_process` / `exec` called with shell=True /
  shell interpolation and user-controlled input?
- Are template engines used to render user input into HTML without
  autoescaping? (XSS risk.)
- Is `eval()`, `exec()`, `Function()`, or equivalent used on
  user-controlled strings?

### 4.2 Input validation
- Is all input from external sources (HTTP parameters, headers, cookies,
  file uploads, message queue payloads, environment variables) validated
  for type, length, range, and format before use?
- Are path components validated to prevent path traversal
  (`../../etc/passwd`)?
- Are file upload types validated by content inspection (magic bytes), not
  just by the `Content-Type` header or file extension?
- Are integer inputs checked for overflow / underflow before arithmetic?
- Are URL / redirect targets validated against an allowlist to prevent
  open-redirect vulnerabilities?

### 4.3 Hardcoded secrets
- Are passwords, API keys, tokens, private keys, or connection strings
  hardcoded in source files (including test fixtures, configuration files,
  and comments)?
- Are secrets logged at any log level?
- Are secrets present in exception messages or stack traces that might be
  captured by a monitoring system?
- Are default credentials left unchanged from library examples or
  documentation?

### 4.4 Unsafe deserialization
- Is `pickle.loads`, `yaml.load` (without `Loader=yaml.SafeLoader`),
  `marshal.loads`, Java's `ObjectInputStream`, PHP's `unserialize`,
  Ruby's `Marshal.load`, or equivalent called on untrusted data?
- Are JSON payloads deserialized into types with executable or privilege-
  bearing attributes (`__class__`, `__reduce__`, prototype pollution in JS)?
- Is XML parsed with external entity expansion enabled (XXE)?

### 4.5 Authentication and authorisation
- Are authorization checks applied consistently on every endpoint /
  handler, or are some paths unprotected by accident?
- Are access control decisions made based on user-supplied data that the
  server has not re-validated server-side (client-side auth bypass)?
- Are JWTs or session tokens validated for signature, expiry, and audience
  before their claims are trusted?
- Are passwords stored with a modern adaptive hashing algorithm (bcrypt,
  Argon2, scrypt)? Storing plain-text, MD5, or SHA-1 hashed passwords is
  CRITICAL.

### 4.6 Dependency and supply-chain risks
- Are dependency versions pinned (exact version or locked via lockfile)?
  Unpinned dependencies (`>=1.0`, `*`) can pull in malicious upgrades.
- Are dependencies known to have CVEs (check against a vulnerability
  database)? Flag any that are obviously outdated or abandoned.
- Are `pip install`, `npm install`, or equivalent run with elevated
  privileges in deployment scripts?
- Is `--trusted-host` / `--allow-insecure` / `--ignore-certificate-errors`
  used in dependency installation, bypassing TLS verification?

### 4.7 Sensitive data exposure
- Is sensitive data (PII, financial data, health records) stored or
  transmitted without encryption?
- Are HTTP endpoints used where HTTPS is required?
- Are database connection strings, cloud credentials, or internal service
  URLs returned in API responses?
- Are stack traces or internal error details returned to API consumers
  in production?

### 4.8 Cryptography
- Are custom cryptographic routines implemented instead of using
  well-audited libraries?
- Are weak or broken algorithms used (MD5, SHA-1 for integrity, DES,
  RC4, ECB mode AES)?
- Are IVs / nonces reused across encryptions with the same key?
- Is `random` / `Math.random()` (non-cryptographic) used where
  `secrets` / `crypto.randomBytes()` (cryptographically secure) is needed?
