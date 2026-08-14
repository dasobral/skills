# Cognitive Debt Categories

Full checklist for the `cognitive-debt` skill. Work through all seven
categories. For each finding, record a concrete file:line reference, quote
the problematic code, explain the cognitive cost, and provide an actionable
recommendation.

Apply `judgment-guidelines.md` throughout — do not flag intentional design.

---

## D1 — Dead Code

Dead code forces readers to wonder "is this used somewhere I haven't looked
yet?" and to trace call chains that lead nowhere. It inflates the mental model
of the system without contributing to its behaviour.

### What to look for

**Unused functions and methods**
- Functions defined but never called within the visible scope
- Methods that exist only because a base class requires them but do nothing
- `pub`/`export`/`public` symbols that are not part of any documented API
  and have no external callers

**Unreachable branches**
- Conditions that are always true or always false given their context
- `else` branches after an early `return` / `throw` / `panic`
- `case` or `match` arms that can never be reached given the type
- Code after `return`, `break`, `continue`, `raise`, `panic!`

**Commented-out code blocks**
- Multi-line blocks of code commented out (not documentation comments)
- Blocks with TODO/FIXME that have been dormant for an extended period
- Old implementations left alongside new ones "just in case"

**Always-on / always-off feature flags**
- Flag values hard-coded to `true` or `false` in source (not config)
- Environment-specific constants that make one branch permanently dead
- Feature flags where the "off" path has never been exercised in practice

### Per-language heuristics

**Python**
- `def` not referenced in the same file or by any `import` — check with Grep
- `if False:` / `if True:` blocks
- `pass`-only implementations of abstract methods that should raise
  `NotImplementedError` (indicates the ABC is unused)
- `# type: ignore` on a dead branch that was left to avoid import errors
- Threshold: flag any unused function with > 5 lines of body

**TypeScript / JavaScript**
- `export`ed symbols not imported anywhere in the project
- `never` type in a `switch`/`if` exhaustive check that is bypassed
- `console.log` debug statements left in production paths
- Dead code inside `if (process.env.NODE_ENV === 'test')` blocks outside
  test files
- Threshold: flag any unexported function with > 3 lines of body that has
  zero call sites

**Rust**
- `#[allow(dead_code)]` on a non-trivial function — compiler already catches
  it; the annotation suppresses a real signal
- `pub` items in a private module with no `pub use` re-export
- `todo!()` / `unimplemented!()` in production code paths that are reachable
- Threshold: flag any item that triggers `dead_code` lint when the annotation
  is mentally removed

**C++**
- Private member functions never called within the class
- `#ifdef` blocks with macros never defined in any build configuration
- Virtual methods with no override in any known concrete class
- `[[maybe_unused]]` on a non-trivial function in a non-template context
- Threshold: flag any private method with > 5 lines that has zero calls

**Go**
- Exported functions with no callers within the module (verify with Grep —
  may be part of a library API; mark `[UNCERTAIN]` if unsure)
- `_ = someVar` assignments that suppress "unused variable" without intent
- Build tag–gated code where the tag is never specified in CI
- Threshold: flag unexported functions with > 5 lines and zero call sites

### Calibration

Do NOT flag:
- Public API surface of a library (may be used by external consumers)
- Test helpers used only in test files
- Interface implementations required by an external framework
- Code guarded by legitimate feature flags configured via external config
- Conditional compilation for platform/arch targets in systems code

---

## D2 — Over-Engineering

Over-engineering forces readers to learn an abstraction layer whose
complexity exceeds the problem it solves. It multiplies the concepts that
must be held in mind simultaneously.

### What to look for

**ABCs / interfaces with exactly one implementation**
- An abstract class, interface, or trait that is only ever instantiated as
  one concrete type and has no visible plans for extension
- Protocol / interface defined and immediately implemented with no other
  consumers

**Plugin registries and factory systems for fixed sets**
- A `Registry`, `Factory`, or `Dispatcher` that maps string keys to types, but
  the set of types is known at compile time and never changes at runtime
- Dependency injection containers used for a handful of singletons that
  could be direct references

**Builders for trivial objects**
- Builder pattern where the object has ≤ 3 fields and all are required
- Builder that does no validation and only assigns values

**Premature generics / type parameters**
- Generic functions or types parameterised over types that are only ever
  instantiated with one concrete type
- Type parameters with no constraints that exist purely for symmetry with
  another generic in a different file

**Configuration objects for single-call-site settings**
- An `Options` / `Config` struct passed to a function that has exactly one
  call site, where all fields are always set to the same values

**Event systems for synchronous, same-process communication**
- Full pub/sub or event bus infrastructure for events that always have
  exactly one subscriber and could be a direct function call

### Per-language heuristics

**Python**
- `abc.ABC` subclass with one concrete implementation in the same file or
  module, no `__all__` export suggesting it's a public extension point
- `**kwargs` forwarding through two or more layers without documentation
- Dataclass with a `build()` or `create()` classmethod acting as a builder
  for ≤ 3 fields
- Threshold: ABC with exactly one concrete implementation is always flagged

**TypeScript / JavaScript**
- `interface IFoo` + `class FooImpl implements IFoo` pattern with one impl
- Generic function `<T extends object>` where T is always inferred as the
  same specific type at the only call site
- `EventEmitter`-based communication between two classes in the same file
- Threshold: generic with single instantiated type is 🟡 MEDIUM; ABC with
  one impl is 🔴 HIGH

**Rust**
- Trait with exactly one `impl` that is not in a position to be mocked
  (i.e., not used in tests via generics or dynamic dispatch)
- `Box<dyn Trait>` where the concrete type is always the same and the value
  is never stored behind an interface boundary (could be a concrete type)
- Builder pattern for a struct where all fields are `pub` and could be set
  directly
- Threshold: single-impl trait used only with static dispatch → 🟡 MEDIUM
  (may be for future extension — mark `[UNCERTAIN]`)

**C++**
- Pure virtual base class with one derived class, no virtual destructor in a
  public header (suggests the abstraction was not designed for external use)
- Template class instantiated with exactly one type throughout the codebase
- Prototype / abstract factory for a fixed set of 2–3 product types
- Threshold: single-instantiation template in a non-library context → 🟡 MEDIUM

**Go**
- Interface defined in the same package as its only implementation
  (Go idiom is to define interfaces at the consumer, not the producer)
- `interface{ Method() }` defined locally and only satisfied by one struct
  outside of test usage
- Threshold: producer-side interface with one impl → 🟡 MEDIUM; flag as
  [UNCERTAIN] if the package is intended as a library

### Calibration

Do NOT flag:
- Interfaces / traits used for testing (even if one production impl exists)
- Extension points documented as intentional API surface
- Generics used for type safety (e.g. `Id<User>` vs `Id<Post>`) even with
  few instantiations
- Builders for objects with complex validation logic regardless of field count
- Plugin systems where external plugins are loaded at runtime

---

## D3 — Duplication

Duplication fragments the reader's model of the system. When logic exists in
multiple places, a reader cannot know which copy is authoritative and must
track all copies when making a change.

### What to look for

**Exact duplication**
- Copy-pasted functions with identical or near-identical bodies
- Identical conditional blocks in multiple locations
- The same SQL query written in three different service methods

**Structural duplication**
- Functions that perform the same sequence of steps (validate → transform →
  persist) but differ only in the types involved, with no shared abstraction
- Parallel class hierarchies that mirror each other's structure

**Semantic duplication**
- Two functions that compute the same logical result using different
  implementations
- Utility helpers that re-implement functionality from the standard library
  or an already-imported dependency

**Magic constants repeated across files**
- Numeric literals like `86400`, `1024`, `200`, `404` appearing in multiple
  source files without a named constant
- String keys like `"user_id"`, `"Authorization"`, `"application/json"` used
  in more than two files without a shared definition

### Per-language heuristics

**Python**
- Two functions whose bodies differ by < 20% (excluding names and types)
- `TIMEOUT = 30` defined at module level in more than one file
- Repeated `try: ... except Exception: logger.error(...)` blocks — should be
  a decorator or context manager
- Threshold: identical block of ≥ 5 lines repeated ≥ 2 times → 🔴 HIGH;
  magic literal in ≥ 3 files → 🟡 MEDIUM

**TypeScript / JavaScript**
- Repeated type assertions (`as SomeType`) in multiple call sites for the
  same value
- The same `fetch`/`axios` call pattern duplicated across services without
  a shared client
- `Object.keys(x).forEach(...)` pattern duplicated when `Object.entries`
  with a shared helper would unify it
- Threshold: same literal string in ≥ 3 files without a `const` → 🟡 MEDIUM

**Rust**
- Identical `match` arms duplicated in two functions that handle the same
  enum
- Repeated `.unwrap_or_else(|e| { error!("{}", e); default })` patterns
  that should be a method or macro
- Two modules with identical `pub use` re-exports
- Threshold: identical `match` block ≥ 4 arms duplicated → 🔴 HIGH

**C++**
- Copy-pasted resource management (open/close, lock/unlock) outside of RAII
  wrappers — each copy is a potential leak
- Repeated raw loop over the same container type where a named algorithm
  (`std::find_if`, etc.) would unify it
- Magic `const int MAX_RETRY = 3` defined in multiple translation units
- Threshold: resource management pattern duplicated ≥ 2 times → 🔴 HIGH
  (correctness risk overlaps with debt)

**Go**
- Repeated `if err != nil { return err }` is idiomatic — do NOT flag
- Repeated `if err != nil { log.Error(...); return err }` in the same
  package where a shared helper would reduce noise → 🟢 LOW
- Identical struct definitions in two packages where embedding or a shared
  type would suffice
- Threshold: identical function body ≥ 8 lines duplicated → 🔴 HIGH

### Calibration

Do NOT flag:
- Intentional duplication at package/service boundaries to avoid coupling
  (e.g. two microservices that independently define a `User` struct)
- Test setup code that is deliberately explicit for readability
- Repeated patterns that are language idioms (`if err != nil` in Go)
- Near-duplication where the differences are semantically significant

---

## D4 — Abstraction Quality

Poor abstractions tax readers twice: once to learn the abstraction's interface,
and again to discover what it actually does underneath. Good abstractions
reduce what a reader must hold in mind; bad ones expand it.

### What to look for

**Leaky abstractions**
- An abstraction that forces callers to know implementation details
  (e.g. a `Cache` that requires callers to know the serialisation format)
- A method that returns an internal type, exposing the implementation
- An interface whose method signatures include infrastructure concerns
  (`DatabaseConnection`, `HttpClient`) that callers must supply

**Misnamed abstractions**
- A class named `Manager`, `Handler`, `Helper`, `Util`, or `Processor`
  with no clear single responsibility indicated by the name
- A function named `process()`, `handle()`, or `do()` with no indication
  of what it processes, handles, or does
- A module named `utils` or `helpers` containing unrelated functions

**God objects**
- A class with > 10 public methods spanning multiple unrelated concerns
- A file > 500 lines that mixes data access, business logic, and presentation
- A single class that both owns and transforms data across more than one
  domain concept

**Shallow wrappers**
- A class that wraps another class but adds no logic, validation, or
  transformation — all methods delegate directly
- A function that calls exactly one other function with the same arguments
  and no additional logic

**Anemic models**
- Domain objects that contain only data (getters/setters) with all logic
  externalized into service classes
- Data classes with no behaviour that are manipulated entirely by surrounding
  procedural code

### Per-language heuristics

**Python**
- Class with > 10 public methods and the methods span more than two
  conceptually distinct concerns
- Module-level function named `process_*` or `handle_*` with > 15 lines
  and no docstring
- Dataclass used only as a dict with type annotations — consider if a
  TypedDict or NamedTuple would be clearer
- Threshold: god class > 10 public methods → 🔴 HIGH; shallow wrapper
  (all methods are one-liners delegating to another object) → 🟡 MEDIUM

**TypeScript / JavaScript**
- `class FooService` with methods spanning HTTP handling, validation,
  DB access, and formatting
- Utility file with > 10 unrelated exported functions (a drawer of
  miscellaneous items)
- `interface IFoo` with a method `process(data: any): any`
- Threshold: service class > 300 lines mixing concerns → 🔴 HIGH

**Rust**
- `impl Foo` block with > 15 methods where methods span I/O, computation,
  and state mutation
- `struct Context` or `struct State` passed through every function as a
  catch-all bag
- Trait with methods that span unrelated concerns (violates Interface
  Segregation — less common in Rust but possible)
- Threshold: struct with > 15 `pub` methods → 🟡 MEDIUM; check if Split
  into multiple traits/types is feasible

**C++**
- Class with both `public:` data members and > 5 methods — unclear whether
  it's a value type or a behaviour type
- Header file > 300 lines that is `#include`d by everything — a "hub"
  include
- `Manager` class with > 10 methods that spans resource allocation,
  business rules, and I/O
- Threshold: hub include or god class → 🔴 HIGH

**Go**
- `struct` with > 10 exported methods spanning multiple conceptual domains
- Package `util` or `common` with > 10 unrelated functions
- Interface with > 5 methods where subsets of methods are never used
  together by any single caller (suggests it should be split)
- Threshold: "mega-interface" (> 5 methods, no caller uses all) → 🟡 MEDIUM

### Calibration

Do NOT flag:
- God objects in generated code
- `Manager` naming that is idiomatic in the framework in use
  (e.g. Django's `objects` manager)
- Shallow wrappers that exist to decouple a third-party library
- Anemic models in read-model / DTO / view-model contexts where behaviour
  belongs in a command handler

---

## D5 — Control Flow Complexity

Complex control flow requires readers to simulate the program's execution
mentally. Each level of nesting, each implicit state transition, and each
use of exceptions for flow control adds to this simulation cost.

### What to look for

**Deep nesting**
- Functions with indentation depth > 3 (counting from the function body)
- Nested `if`/`for`/`with`/`try` blocks where early returns or guard clauses
  would flatten the structure

**Implicit state machines**
- A sequence of boolean flags (`is_started`, `is_processing`, `is_done`)
  that collectively encode a state machine but are managed ad-hoc
- `status` strings like `"pending"`, `"running"`, `"done"` mutated through
  a chain of `if/else` conditions without a formal state enum

**Exception-driven flow**
- Using `try/except` or `try/catch` to distinguish expected outcomes
  (not error recovery) — e.g. `try: return cache[key] except KeyError: ...`
  where a `.get(key)` would be clearer
- Raising exceptions to exit a loop or signal a non-error condition

**Long functions**
- Functions > 40 lines that cannot be read on a single screen
- Functions that mix multiple levels of abstraction (network call + string
  parsing + business rule in the same function body)

**Complex conditionals**
- Boolean expressions with > 3 `and`/`or`/`&&`/`||` operators not broken
  into named predicates
- Nested ternary operators

### Per-language heuristics

**Python**
- Nesting depth > 3 → 🔴 HIGH; refactor with early returns or extracted helpers
- `except Exception:` with `pass` or only a log → always 🔴 HIGH (swallowed error)
- `try/except KeyError` for dict access instead of `.get()` → 🟢 LOW
- Threshold: function > 40 lines → 🟡 MEDIUM; > 80 lines → 🔴 HIGH

**TypeScript / JavaScript**
- Callback pyramid (> 3 levels of nested callbacks) that was not converted
  to `async/await` → 🔴 HIGH
- Long chains of `.then().catch().then()` mixing error and success paths
  → 🟡 MEDIUM
- Complex ternary: `a ? b ? c : d : e ? f : g` → 🔴 HIGH
- Threshold: function > 40 lines → 🟡 MEDIUM; > 80 lines → 🔴 HIGH

**Rust**
- `match` arms that themselves contain `match` expressions more than 1
  level deep → 🟡 MEDIUM
- `unwrap()`/`expect()` chains where `?` propagation is available
  → 🟡 MEDIUM in library code, 🟢 LOW in binaries/tests
- Using `panic!` in non-panic contexts to handle recoverable errors → 🔴 HIGH
- Threshold: function > 40 lines (excluding comments/blank lines) → 🟡 MEDIUM

**C++**
- Nesting depth > 4 → 🔴 HIGH
- `goto` for flow control (not cleanup in C-style code) → 🔴 HIGH
- Long `if/else if` chains over an enum without `switch` → 🟡 MEDIUM
- Threshold: function > 50 lines → 🟡 MEDIUM; > 100 lines → 🔴 HIGH

**Go**
- `err != nil` chains that span > 20 lines without any extraction → 🟡 MEDIUM
- Goroutine spawned without a corresponding `WaitGroup` or `context.Done`
  exit path (correctness overlap — flag as 🔴 HIGH)
- Deeply nested `select` + `for` combinations without comments explaining
  the state machine intent → 🟡 MEDIUM
- Threshold: function > 40 lines → 🟡 MEDIUM

### Calibration

Do NOT flag:
- `try/except` for genuinely exceptional conditions (network errors, file not found)
- Pattern matching (`match`/`switch`) with many arms when the alternatives
  are worse
- Error-propagation chains that are idiomatic (`?` in Rust, `if err != nil` in Go)
- Long functions in generated code or data tables

---

## D6 — Naming

Poor names force readers to hold parallel mental translations: "when the code
says `tmp`, I need to remember it means the deserialized user record." Good
names collapse the gap between what the code says and what it means.

### What to look for

**Non-predicate boolean names**
- Boolean variables or return types named without a predicate prefix:
  `active` (vs `isActive`), `error` (vs `hasError`), `valid` (vs `isValid`)
- Method returning `bool` without a predicate form: `user.admin()` vs
  `user.isAdmin()`

**Implementation-describing names**
- Names that describe the mechanism, not the intent:
  `parseAndValidateAndStore()`, `getFromCacheOrFetch()`,
  `loopOverUsersAndSendEmail()`
- Variable names like `data`, `result`, `response`, `obj`, `temp`, `tmp`,
  `info` with no domain meaning in a non-trivial scope

**Opaque abbreviations**
- Single-letter variables outside conventional scopes (`i`, `j`, `k` in
  loops; `e` in exception handlers; `n` for numeric counts)
- Abbreviations that are not widely understood in the domain:
  `usr`, `cfg`, `mgr`, `svc`, `proc`, `param` (context-dependent)
- Names that require reading the implementation to understand:
  `handle`, `payload`, `context` used without qualification

**Misleading names**
- A function named `get*` that has visible side effects
- A function named `validate*` that also transforms data
- A boolean named `disabled` where `true` means enabled (inverted semantics)

**Inconsistent terminology**
- `User`, `Account`, `Member`, `Principal` used for the same domain concept
  in different files
- `fetch`, `get`, `retrieve`, `load`, `read` used interchangeably for the
  same operation

### Per-language heuristics

**Python**
- `is_`, `has_`, `can_`, `should_` prefix required for boolean attributes/returns
- Single-letter names acceptable only in: list comprehensions, lambdas with
  obvious types, numeric loop variables
- `_private` naming must be respected — flag if `_` items are accessed
  externally without justification
- Threshold: non-predicate boolean in a public API → 🔴 HIGH; in a local
  variable in a > 20-line function → 🟡 MEDIUM

**TypeScript / JavaScript**
- `is`, `has`, `can`, `should` prefix for boolean-returning functions
- `any`-typed parameter named `data` or `payload` in a non-generic function
  — the name should reflect the domain → 🟡 MEDIUM
- Callback parameter named `e` outside event handlers, `res` outside HTTP
  handlers — abbreviations leak their context
- Threshold: misleading name (e.g. `get*` with side effects) → 🔴 HIGH

**Rust**
- Rust community conventions: `is_*`/`has_*` for `bool`-returning methods;
  `new`, `default`, `from_*` for constructors — deviations are debt
- Lifetime names: `'a`, `'b` are fine in simple cases; in functions with ≥ 3
  lifetimes, meaningful names (`'request`, `'session`) reduce confusion
- Type parameter `T` is fine; `T1`, `T2`, `T3` without names → 🟡 MEDIUM
- Threshold: public API method that mutates state but is named `get_*` → 🔴 HIGH

**C++**
- Hungarian notation (unless codebase-wide and enforced) → 🟢 LOW to flag
  as inconsistent if mixed
- `void process(Data* d)` — meaningless parameter name in a non-trivial
  function → 🟡 MEDIUM
- `m_` prefix not used consistently across class members → 🟢 LOW
- Threshold: misleading const (`MAX_SIZE` used as a minimum check) → 🔴 HIGH

**Go**
- Go idiom: short names in short functions; longer names in longer functions
  — do NOT flag `u` for `user` in a 5-line function
- Exported names must be self-documenting: `ServerConfig` not `Config` if
  multiple configs exist
- Interface name should end in `-er` if it has one method; flag multi-method
  interfaces with `-er` names → 🟢 LOW
- Threshold: exported function with a name that describes implementation over
  intent → 🟡 MEDIUM

### Calibration

Do NOT flag:
- Conventional short names: `i`, `j`, `k` in loops; `err` in Go; `e` in
  Python except clauses; `ctx` for context; `req`/`resp` in HTTP handlers
- Domain abbreviations that are well-established in the codebase (if they
  appear consistently, they are vocabulary, not debt)
- `_` for intentionally ignored values

---

## D7 — Test Debt

Test debt undermines confidence in the test suite itself, making it harder to
know whether a passing test suite means the code is correct.

### What to look for

**Over-mocking**
- Tests that mock every dependency, including pure functions with no I/O
- Tests where more code is mock setup than assertion
- Mocks that encode implementation details (the test breaks if you rename
  a private method even though the behaviour is unchanged)

**Skipped tests**
- `@pytest.mark.skip`, `xit`, `xdescribe`, `t.Skip()`, `#[ignore]`,
  `GTEST_SKIP()` without a comment explaining why and a linked issue
- Commented-out test bodies

**Trivial assertions**
- Tests that assert the return value equals the input (testing no logic)
- Tests that only assert a function does not throw, with no behaviour verified
- Snapshot tests that snapshot the entire output of a complex function
  (obscures what is being tested)

**Test-only production code**
- Production code with `if testing:` / `if os.Getenv("TEST") != ""` branches
- Public methods that exist solely to enable test access to private state

**Missing tests for critical paths**
- `[UNCERTAIN]` — flag when a complex function (> 20 lines, > 2 branches)
  has no corresponding test file or test reference; cannot always confirm
  from static analysis

### Per-language heuristics

**Python**
- `unittest.mock.patch` on a function in the same module under test → 🟡 MEDIUM
  (indicates over-coupling to implementation)
- `assert result is not None` as the only assertion → 🟢 LOW to 🟡 MEDIUM
  depending on criticality of the code under test
- Threshold: test file where mock/patch lines exceed assertion lines → 🔴 HIGH

**TypeScript / JavaScript**
- `jest.mock()` of a pure utility function → 🟡 MEDIUM
- `expect(fn).not.toThrow()` as the only assertion → 🟡 MEDIUM
- `it.skip` / `xit` without explanation → 🟡 MEDIUM; if > 2 weeks stale
  (check git blame) → 🔴 HIGH
- Threshold: > 50% of test body is mock setup → 🟡 MEDIUM

**Rust**
- `#[ignore]` without a comment → 🟡 MEDIUM
- Test that calls `unwrap()` on the result under test — hides the actual
  error when the test fails → 🟢 LOW (but worth noting)
- Test only asserts `assert!(result.is_ok())` → 🟡 MEDIUM
- Threshold: test module with only trivial `is_ok()` assertions → 🟡 MEDIUM

**C++**
- `GTEST_SKIP()` without comment → 🟡 MEDIUM
- Test with `EXPECT_TRUE(true)` or always-true condition → 🔴 HIGH
- Tests that access private members via `friend class Test*` instead of
  testing through the public interface → 🟡 MEDIUM
- Threshold: `DISABLED_` prefixed tests (GTest convention for skip) without
  linked issue → 🟡 MEDIUM

**Go**
- `t.Skip("TODO")` without a ticket or explanation → 🟡 MEDIUM
- Test helper that returns a value without calling `t.Fatal` on error
  (caller must remember to check) → 🟡 MEDIUM
- `if testing.Short() { t.Skip() }` is idiomatic — do NOT flag
- Threshold: test function > 100 lines with > 50% mock setup → 🔴 HIGH

### Calibration

Do NOT flag:
- Mocking of I/O boundaries (database, HTTP, filesystem) — this is correct
- Integration tests that are skipped in short/unit mode with a clear comment
- Snapshot tests for UI components where snapshots are reviewed on change
- Tests of error paths that necessarily test "does not throw"
