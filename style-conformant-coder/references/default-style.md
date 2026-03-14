# Default Style Reference

Per-language style defaults used as fallback when no `CODING_REQUIREMENTS.md`
exists. These are opinionated but clean — the result of distilling widely
accepted community standards into concrete rules.

---

## Python

### Formatting
- Line length: 88 characters (Black-compatible).
- 4-space indentation. No tabs.
- Two blank lines between top-level definitions; one between methods.
- Trailing commas in multi-line collections.

### Naming
- `snake_case` for functions, variables, module names.
- `PascalCase` for classes.
- `UPPER_SNAKE_CASE` for module-level constants.
- Single leading underscore for internal-use names; double only when
  name-mangling is genuinely needed.

### Idiomatic constructs — USE

| Construct | Rationale |
|-----------|-----------|
| List/dict/set comprehensions | Clearer than equivalent `for` loops when the body is a single expression |
| `pathlib.Path` | Type-safe, composable path handling — never `os.path` |
| f-strings | Faster and more readable than `.format()` or `%` formatting |
| `dataclasses` | Eliminates hand-rolled `__init__` / `__repr__` / `__eq__` boilerplate |
| `with` statements | Guaranteed resource cleanup |
| `enumerate` / `zip` | Avoid manual index arithmetic |

### Idiomatic constructs — AVOID

| Construct | Why |
|-----------|-----|
| Nested comprehensions deeper than 2 levels | Kills readability — use a loop |
| Bare `except:` or `except Exception:` | Swallows unexpected errors silently |
| `os.path` | Replaced by `pathlib` |
| Mutable default arguments (`def f(x=[])`) | Shared across calls — always a bug |
| `Optional[X]` | Use `X \| None` (Python 3.10+) |
| `str.format()` / `%` formatting | Use f-strings |

### Error handling
- Raise the most specific exception type available.
- Custom exceptions inherit from the nearest appropriate built-in
  (`ValueError`, `RuntimeError`, `OSError`, etc.).
- Never catch and re-raise the same exception without adding context.
- Use `contextlib.suppress` for deliberate swallowing only when the intent
  is self-evident.

### Comments and docstrings
- Public functions and classes get a one-line docstring if the name alone
  is insufficient. Three-line format (summary, blank, detail) when more is
  needed.
- Inline comments only for non-obvious logic. Never restate what the code
  does.
- No `# type: ignore` without a brief explanation on the same line.

### Type annotations
- All public function signatures require type hints.
- Return type always annotated, including `-> None`.
- Use `X | None` not `Optional[X]` (3.10+).
- `list[T]`, `dict[K, V]`, `tuple[T, ...]` — not `List`, `Dict`, `Tuple`
  from `typing` (3.9+).

---

## C++

### Standard
- C++17 minimum. Use C++20 features (`std::span`, ranges, concepts,
  `std::format`) where the toolchain supports them.

### Formatting
- 4-space indentation. Opening brace on the same line.
- 100-character line limit.
- `#pragma once` for include guards.

### Naming
- `PascalCase` for types and classes.
- `snake_case` for functions, methods, variables.
- `kCamelCase` or `UPPER_SNAKE_CASE` for constants (pick one per project).
- Private members: `trailing_underscore_` or `m_prefix` — be consistent.

### Idiomatic constructs — USE

| Construct | Rationale |
|-----------|-----------|
| RAII everywhere | Deterministic cleanup; no manual resource management |
| `std::unique_ptr` as default | Single ownership, zero overhead |
| `const` by default | Prevents accidental mutation; improves optimisation |
| `[[nodiscard]]` | Forces callers to check return values that matter |
| `std::optional<T>` | Expresses nullable return without sentinel values |
| `std::string_view` for non-owning string params | Avoids copies from literals and `std::string` |
| Structured bindings | Cleaner decomposition of pairs and tuples |
| Range-based `for` | Prefer over index loops unless the index is needed |

### Idiomatic constructs — AVOID

| Construct | Why |
|-----------|-----|
| Raw owning pointers (`new` / `delete`) | RAII exists — use it |
| `shared_ptr` by default | Ownership overhead; reach for `unique_ptr` first |
| `using namespace std;` in headers | Pollutes every translation unit that includes the header |
| C-style casts | `static_cast` / `reinterpret_cast` make intent explicit |
| `std::endl` in hot paths | Flushes the buffer; use `'\n'` |
| Exception-heavy hot paths | Use `std::expected` / result types for recoverable errors |
| `#define` for constants | `constexpr` is typed and scoped |

### Error handling
- Exceptions for truly exceptional, unrecoverable conditions.
- `std::expected<T, E>` (C++23) or a thin result type for recoverable
  errors in hot paths.
- Never swallow exceptions with an empty `catch` block.
- Destructors must not throw.

### Comments
- `/** Doxygen */` for public API. One-line `///` for obvious members.
- `// SAFETY:` comment required before every cast that could invoke
  undefined behaviour.
- `// TODO(owner):` not `// TODO:`.

---

## Rust

### Formatting
- `rustfmt` defaults. 100-character line limit.
- One blank line between items at module level; none between closely
  related items.

### Naming
- `snake_case` for functions, methods, variables, modules.
- `PascalCase` for types, traits, enums.
- `UPPER_SNAKE_CASE` for constants and statics.
- Avoid single-letter names except in closures and iterator chains where
  the type is obvious.

### Idiomatic constructs — USE

| Construct | Rationale |
|-----------|-----------|
| `?` for error propagation | Clean, composable; propagates without `unwrap` |
| `thiserror` for library error types | Derives `std::error::Error` with minimal boilerplate |
| `anyhow` for application-level errors | Context-rich error chains for binaries |
| Iterator chains | Expressive, often zero-cost after optimisation |
| Pattern matching over `if let` chains | Exhaustive, prevents missed cases |
| `impl Trait` in return position | Hides concrete type cleanly |

### Idiomatic constructs — AVOID

| Construct | Why |
|-----------|-----|
| `.unwrap()` in library code | Panics on bad input — use `?` or explicit handling |
| `.clone()` to satisfy the borrow checker | Fix the ownership model instead |
| `unsafe` without `// SAFETY:` comment | Every `unsafe` block requires a documented justification |
| `Box<dyn Error>` in library APIs | Erases type info — use `thiserror` instead |
| `std::mem::transmute` without explicit review | Near-always avoidable; document why it cannot be avoided |

### Error handling
- `?` for propagation everywhere — never `.unwrap()` in library code.
- Define error types with `thiserror` in libraries; use `anyhow` in
  application binaries.
- Every `unsafe` block must be preceded by a `// SAFETY:` comment that
  explains why the invariants are upheld.

### Comments
- Doc comments (`///`) on all public items.
- `//` inline comments only for non-obvious logic.
- `// SAFETY:` required before every `unsafe` block (treated as a hard
  rule, not a style note).
- `#[allow(...)]` attributes require an explanatory comment.

### Type annotations
- Let type inference work; annotate where the type is not obvious from the
  right-hand side or when it documents intent.
- Always annotate function signatures fully.

---

## Go

### Formatting
- `gofmt` / `goimports` enforced. No manual formatting debates.
- Standard 80-character soft limit; 100 hard limit for complex expressions.

### Naming
- `camelCase` for unexported identifiers; `PascalCase` for exported.
- Short, contextual variable names in small scopes (`i`, `n`, `err`);
  descriptive names for package-level or long-lived variables.
- Acronyms: `URL`, `HTTP`, `ID` — not `Url`, `Http`, `Id`.
- Interface names: single-method interfaces end in `-er` (`Reader`,
  `Stringer`). Multi-method interfaces use descriptive nouns.

### Idiomatic constructs — USE

| Construct | Rationale |
|-----------|-----------|
| Multiple return values for errors | Go's standard error model |
| `errors.Is` / `errors.As` | Sentinel and typed error checking |
| `fmt.Errorf("...: %w", err)` | Wraps errors with context |
| Table-driven tests | Keeps test cases explicit and extensible |
| `defer` for cleanup | Pairs resource acquisition and release visually |
| Interfaces for testability | Accept interfaces, return concrete types |

### Idiomatic constructs — AVOID

| Construct | Why |
|-----------|-----|
| Returning `error` and ignoring it at call site | Always check errors |
| `init()` with side effects | Hard to test and reason about |
| Empty interface (`interface{}` / `any`) when a concrete type will do | Loses type safety |
| Goroutine leaks (no done channel) | Always provide a cancellation path |
| Named return values except for documentation | Leads to confusing `return` statements |

### Error handling
- Every error return must be checked — never `_` an error silently.
- Wrap errors with `fmt.Errorf("context: %w", err)` to preserve the chain.
- Define sentinel errors with `var ErrFoo = errors.New("...")` at package
  level; typed errors with a struct implementing `error`.

### Comments
- Every exported identifier gets a doc comment starting with its name.
- Package-level comment on one file in the package.
- Inline comments only for non-obvious logic.

### Type annotations
- Go infers types — use `:=` in function bodies; use explicit types for
  package-level vars and when the type documents intent.

---

## TypeScript

### Formatting
- Prettier defaults: 2-space indent, 100-character line limit, single
  quotes, trailing commas in multi-line contexts.

### Naming
- `camelCase` for variables, functions, methods.
- `PascalCase` for types, interfaces, classes, enums, React components.
- `UPPER_SNAKE_CASE` for module-level constants.
- Prefix interfaces with `I` only if the project already does so — do not
  introduce the convention unilaterally.

### Idiomatic constructs — USE

| Construct | Rationale |
|-----------|-----------|
| `const` by default, `let` when mutation is required | `var` is never needed |
| Optional chaining (`?.`) | Safe property traversal without nested null checks |
| Nullish coalescing (`??`) | Default values without clobbering `0` or `''` |
| Discriminated unions | Type-safe state modelling; exhaustive switch checks |
| `readonly` on data that should not mutate | Encodes intent in the type system |
| `satisfies` operator (TS 4.9+) | Type-checks object literals without widening |
| `unknown` over `any` for external data | Forces validation before use |

### Idiomatic constructs — AVOID

| Construct | Why |
|-----------|-----|
| `any` | Disables type checking — use `unknown` and narrow |
| Non-null assertion (`!`) without comment | Silently explodes at runtime if wrong |
| Enum (const enum or plain) for string unions | String literal unions are simpler and serialise correctly |
| `namespace` / `module` keyword blocks | ES modules supersede them |
| `var` | No block scoping, no temporal dead zone — use `const`/`let` |
| Casting with `as` to silence type errors | Fix the type, not the error message |

### Error handling
- `throw` only for genuinely exceptional, unrecoverable conditions.
- Prefer `Result`-style types or explicit `null` returns for expected
  failure paths.
- Never swallow errors in an empty `catch` block.
- `async/await` with `try/catch`; avoid `.catch()` chains that lose stack
  traces.

### Comments and docstrings
- JSDoc (`/** */`) on exported functions and types when the name alone is
  insufficient.
- Inline `//` only for non-obvious logic.
- No `@ts-ignore` without a comment explaining why — prefer `@ts-expect-error`.

### Type annotation expectations
- All function parameters and return types explicitly annotated.
- No implicit `any` (`noImplicitAny: true` assumed).
- Prefer `interface` for object shapes that will be implemented or extended;
  `type` for unions, intersections, and aliases.
