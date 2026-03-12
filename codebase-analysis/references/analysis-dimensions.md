# Analysis Dimensions

Full checklist for the `analyze-codebase` skill. Work through all 16
dimensions. For each, record **concrete, imperative rules** backed by real
file references — not observations.

---

## 1. Architecture & Structure

- Overall pattern: monolith / monorepo / microservices / layered /
  feature-based / domain-driven / hexagonal / clean architecture?
- Top-level directories and their single responsibility.
- Allowed and forbidden dependency directions between layers / modules.
- Where business logic, data access, and presentation each live.
- Dependency injection, service-locator, or factory patterns in use.
- Public API contract style: REST, GraphQL, RPC, events, CLI?
- Monorepo tooling: Nx, Turborepo, Cargo workspaces, Go modules?

## 2. Naming Conventions

- Local variables and parameters.
- Constants and environment variable names.
- Functions and methods — verb conventions, boolean prefix (`is`, `has`,
  `can`, `should`), getter/setter style.
- Classes, structs, records.
- Interfaces, protocols, traits — prefix/suffix conventions (`I`, `Able`,
  `Protocol`)?
- Type aliases, generics, and type parameters (`T`, `TItem`, `K`/`V`?).
- Enums and enum variants.
- Files — casing, separator, suffix conventions (`*.service.ts`,
  `*_handler.go`, `test_*.py`).
- Directories and packages — casing, plural vs. singular.
- Test files and test helper naming.
- Private / internal markers (`_`, `__`, unexported lowercase, `#`).
- Event and message names (if event-driven).

## 3. Code Formatting & Style

- Indentation: tabs vs. spaces; width.
- Quote style: single / double / backtick; template literals usage.
- Maximum line length.
- Semicolon policy.
- Trailing commas (all / multi-line only / never).
- Brace style: same line / next line; omission for single-statement blocks.
- Blank-line rules: between functions, between class members, at file end.
- File encoding and line endings (LF vs. CRLF).
- Tooling: formatter name and version; whether formatting is enforced in CI.

## 4. Module & Import Patterns

- Import ordering and grouping rules (stdlib → third-party → internal;
  alphabetical within groups?).
- Barrel / index file usage: encouraged, discouraged, or prohibited?
- Re-export patterns: are internal modules exposed via a public API layer?
- Path aliases vs. relative imports (when each is used, max depth for
  relative paths).
- Circular dependency policy — detected by linter? prohibited outright?
- Dynamic imports / code splitting conventions.
- Side-effect imports (CSS, polyfills) — where and how?

## 5. Type System & Type Safety

- Strictness level: `strict` mode, `noImplicitAny`, `exactOptionalPropertyTypes`?
- Use of `any`, `unknown`, `never` — when each is permitted.
- Type guards and assertion functions — naming and placement.
- Branded / opaque types — used for IDs, units, currencies?
- Generics — where used, constraints style.
- Utility types in active use (`Partial`, `Pick`, `Readonly`, custom).
- Schema-first vs. type-first: are runtime types derived from TS types or
  vice versa?
- Coercion vs. parsing at system boundaries.

## 6. Async & Concurrency Patterns

- Primary async model: async/await, promises, callbacks, goroutines,
  threads, actors, reactive streams?
- Error propagation in async code: rejected promises, `Result`, exceptions?
- Concurrency primitives in use: mutexes, channels, semaphores, queues?
- Timeout and cancellation conventions (AbortController, context passing).
- Rate-limiting and retry patterns (libraries or custom?).
- Background job / worker patterns.
- Real-time patterns: WebSockets, SSE, polling — and their abstractions.

## 7. Error Handling

- Propagation strategy: exceptions / `Result<T,E>` / `(value, error)` tuples
  / error codes / discriminated unions?
- Custom error hierarchy: base class, error codes, metadata fields.
- Where errors are caught vs. propagated.
- User-facing error shape: HTTP status codes, JSON error payload structure,
  i18n approach.
- Unhandled rejection / panic policy.
- Error logging at catch sites (what is logged, at what level).

## 8. State & Data Management

- Application state: Redux, Zustand, Pinia, MobX, Context, Signals, Atoms?
  — where global state lives and what goes in local state.
- Server / async state: SWR, React Query, RTK Query, Apollo, custom hooks?
- Forms: controlled / uncontrolled, validation library.
- Persistence layer: ORM / query builder, raw SQL, repository pattern.
- Caching strategy: TTL defaults, cache keys, invalidation approach.
- DTO and schema validation: Zod, Pydantic, class-validator, io-ts?
- Data transformation layer: where and how domain objects are mapped to/from
  API or DB representations.

## 9. Language & Framework Idioms

- Language version and features actively used (ESNext features, Rust
  edition, Python 3.x typing, etc.).
- Framework(s), version(s), and rendering model (SSR, SPA, RSC, etc.).
- Preferred idiomatic patterns (hooks, decorators, middleware, iterators,
  pattern matching, etc.).
- Patterns explicitly avoided or superseded in this codebase.
- Preferred library choices when multiple options exist (date-fns vs.
  moment, axios vs. fetch, etc.).
- Deprecated APIs still present — are they quarantined or being migrated?

## 10. Testing Patterns

- Test pyramid balance: unit / integration / e2e — which layers exist and
  where emphasis lies.
- File co-location vs. separate `tests/` directory.
- Test runner and assertion library.
- Naming: `describe` / `it` / `test` style; what makes a good test name.
- Fixtures, factories, and builders — where they live and how they are used.
- Mock / stub / spy approach: library, manual mocks, test doubles.
- Snapshot testing: used? for what? review policy.
- Coverage thresholds enforced by CI; what is excluded.
- Required tests for PRs (unit only, or integration too?).

## 11. Documentation & Comments

- Docstring / JSDoc convention: all public APIs / complex logic only / none.
- Required fields: `@param`, `@returns`, `@throws`, `@example`?
- Inline comment style: full sentences or fragments; `//` vs. block style.
- `TODO` / `FIXME` / `HACK` conventions — must include ticket reference?
- API documentation tooling: OpenAPI / Swagger, TypeDoc, Sphinx, rustdoc?
- README conventions: what each package / service README must contain.
- Changelog format: Keep a Changelog, conventional commits, auto-generated?

## 12. Logging & Observability

- Logging library and minimum log level per environment.
- Structured vs. plain-text logs; required fields (request ID, user ID,
  trace ID, duration).
- What must always be logged: requests, errors, external calls, job
  start/end?
- What must never be logged: PII, secrets, full payloads?
- Metrics: library, naming convention, cardinality rules.
- Distributed tracing: library, span naming, context propagation.
- Alerting thresholds defined in code vs. infrastructure?

## 13. Security Conventions

- Input validation boundary: where external data is parsed and validated;
  trust model for internal calls.
- Auth / authz pattern: JWT, sessions, RBAC, ABAC, middleware vs. decorator.
- Secret management: env vars, secrets manager, vault — and how they are
  accessed in code.
- Sensitive data handling: PII fields, encryption at rest, masking in logs.
- Dependency security: audit tooling, pinned vs. range versions, update
  policy.
- Common vulnerability mitigations enforced: SQL injection, XSS, CSRF,
  path traversal, etc.

## 14. Performance Patterns

- Memoisation and caching conventions (in-memory, Redis, CDN layers).
- Pagination: default page size, max page size, cursor vs. offset.
- Lazy loading: dynamic imports, deferred initialization, on-demand fetching.
- Database query patterns: N+1 prevention, eager loading rules, index usage.
- Asset optimisation: image formats, bundle splitting, tree shaking.
- Profiling and performance budget enforcement in CI.

## 15. Developer Workflow

- Exact commands to install, start, lint, format, type-check, test, and
  build.
- Pre-commit hooks: what runs, which tool (husky, lefthook, pre-commit).
- CI gates that must pass before merge.
- Branch naming convention.
- Commit message format: Conventional Commits, custom, free-form?
- PR requirements: size limits, required reviewers, linked tickets.
- Release and versioning process: semver, CalVer, automated?

## 16. Anti-patterns Catalogue

For each anti-pattern found in the codebase, record:
- **What**: a clear description of the pattern.
- **Why it's prohibited**: the problem it causes.
- **Instead**: the correct approach.
- **Where seen**: file path(s) where the violation exists (for remediation).

Common categories to check:
- Inconsistent patterns introduced by historical accidents.
- Patterns present in older code that newer code has superseded.
- Library or API usage that has been officially deprecated internally.
- Copy-paste code that was not abstracted.
- Unsafe type coercions or silent error suppression.
- Business logic in the wrong layer.
- Test code in production bundles.
