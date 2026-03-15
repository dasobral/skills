# Judgment Guidelines

These guidelines govern when the `cognitive-debt` skill should **not** flag
something as debt, and how to characterise findings that fall into genuinely
ambiguous territory. Apply these before assigning any severity.

The goal of cognitive debt analysis is to identify *real friction* — patterns
that a neutral, experienced engineer in the target language would agree make
code harder to understand. It is not an exercise in finding violations of
abstract principles.

---

## 1. Do Not Pathologize Intentional Design

Before flagging a pattern, ask: **"Could a reasonable senior engineer have
chosen this deliberately, and would their reasoning hold up to scrutiny?"**

If yes, do not flag it — or flag it with `[UNCERTAIN]` at 🟢 LOW severity,
noting that the pattern appears intentional and explaining why it might still
cause friction.

### Examples of intentional design to respect

**Deliberate extensibility**
An interface with a single implementation today may be an extension point
for tomorrow. If the code has a comment documenting this intent, or if the
surrounding architecture suggests it (e.g. a plugin system, a SDK), do not
flag the single-impl interface.

**Strategic duplication at service boundaries**
Two microservices that independently define a `User` type are not exhibiting
duplication debt. They are respecting the bounded-context boundary to avoid
coupling. Flag only when duplication within a single service/module creates
maintenance risk.

**Verbose error handling for auditability**
A long chain of explicit error checks with logging at each step may look
like over-engineering, but it may be intentional for auditability in a
financial or security-critical context. Check for comments or surrounding
context before flagging.

**Conservative abstractions**
A thin wrapper around an external library (shallow wrapper) may be
intentional to decouple the codebase from that library's API. This is a
legitimate pattern, especially when the wrapped library's API changes
frequently. Note it as potentially intentional rather than debt.

---

## 2. Distinguish Objective Problems from Judgment Calls

Not all cognitive friction is equally objective. Apply these categories:

### Objective — nearly always debt

Flag confidently (CERTAIN):
- Code that cannot be reached by any execution path
- A variable never read after assignment
- A test that asserts `True is True`
- A function that duplicates another function in the same file, line-for-line
- A boolean named `active` (not `isActive`) in a strongly typed public API

### Likely — probably debt, but context matters

Flag as `[UNCERTAIN]` or downgrade one level:
- An ABC with one implementation (might be an extension point)
- A 50-line function (might be fine if it's a data table or a switch case)
- A `Manager` class (might be idiomatic in the framework)
- Deep nesting that mirrors an inherently complex business rule

### Judgment call — reasonable engineers disagree

Flag at 🟢 LOW with a note that trade-offs exist:
- Anemic domain models (some teams intentionally separate data and logic)
- Implicit state machines (might be clearer as code than as a formal enum
  in simple cases)
- Opaque abbreviations that are domain vocabulary (team-specific)

---

## 3. Language Idioms Are Not Debt

Every language has patterns that look like debt to engineers from other
languages but are idiomatic and have good reasons:

| Language | Pattern | Why it is NOT debt |
|----------|---------|-------------------|
| Go | `if err != nil { return err }` repeated throughout | Explicit error propagation is a deliberate language design choice; do not flag |
| Go | Short variable names (`u` for user in a 5-line function) | Idiomatic; Go community style guide endorses this |
| Rust | `unwrap()` in tests | Idiomatic; test panics are acceptable failure modes |
| Rust | `Box<dyn Error>` in `main()` | Idiomatic for application binaries |
| Python | `try/except` for flow control in performance-critical code | EAFP (Easier to Ask Forgiveness than Permission) is idiomatic Python |
| Python | `_private` naming without a leading double underscore | Single underscore is the Python convention for "private by convention" |
| C++ | RAII wrappers that look like shallow wrappers | RAII is a first-class C++ pattern; thin wrappers that manage lifetimes are not debt |
| TypeScript | Intersection types (`A & B`) that look like over-engineering | Often required for correct typing without `any` |

When you encounter a pattern that looks like debt but might be idiomatic,
check `debt-categories.md` for the "Calibration — Do NOT flag" section for
that language.

---

## 4. Framework and Library Constraints

Some patterns that look like over-engineering or over-abstraction are
required by the framework:

- **Django**: `objects` manager; `Meta` inner class; abstract model base classes
- **Rails**: ActiveRecord callbacks; concern modules
- **React**: Higher-order components or render props (legacy patterns, but
  not debt in pre-hooks codebases)
- **Spring**: Interface-per-service for AOP proxy compatibility
- **gRPC**: Generated stubs with shallow wrapper implementations
- **Protocol Buffers**: Anemic message types with only getters/setters

When a pattern is required by the framework in use, do not flag it. Note the
framework constraint if the reader might not be aware of it.

---

## 5. Scale and Context

Thresholds in `debt-categories.md` are calibrated for average production
codebases. Adjust your judgment for:

**Prototype / exploratory code**
If the repository is clearly a prototype (README says so, no CI, no version
history, a single committer), lower severity expectations. Flag only patterns
that will actively harm the team if the prototype becomes production code.

**Generated code**
Never flag generated files (`*.generated.*`, `*_pb2.py`, `*.g.dart`,
`zz_generated_*.go`, `bindings.rs`, etc.) for any debt category. Generated
code cannot be manually improved.

**Third-party vendored code**
Do not analyse vendored dependencies (`vendor/`, `third_party/`, `_deps/`).

**Algorithmic / mathematical code**
Short variable names (`x`, `y`, `dx`, `n`, `k`) in mathematical functions
are conventional. Dense expressions in DSP, linear algebra, or physics
simulations are often correct representations of the mathematical form.

**Configuration files**
Do not flag YAML, JSON, TOML, or other configuration files for structural
debt. They are data, not code.

---

## 6. Flag Uncertainty Inline — Never Hide It

When a finding could be intentional, use this pattern:

```
**[UNCERTAIN]** This pattern looks like X, but may be intentional if Y.
Flagging at 🟢 LOW for awareness. If this is deliberate, a brief comment
explaining the intent would eliminate this as a future concern.
```

Never omit a finding because you are uncertain. Instead, flag it at the
lowest appropriate severity with `[UNCERTAIN]` and explain your uncertainty.
This gives the reader full information and respects their ability to make
the final call.

---

## 7. The Neutrality Test

Before writing a finding, run this test:

> "Would a senior engineer who has never seen this codebase, reading this
> finding in a code review, nod and agree that this is a real problem — or
> would they say 'this looks fine to me'?"

If the answer is "they'd probably say it looks fine," either:
- Lower the severity to 🟢 LOW and add `[UNCERTAIN]`
- Drop the finding entirely

Do not use the report as a vehicle for personal style preferences. Only report
what reduces the ability of a competent reader to understand and modify the code.

---

## 8. Positive Recognition

The report must include a "What's Working Well" section. As you analyse, note:

- Consistent naming conventions applied across the codebase
- Well-bounded abstractions where the name matches the implementation
- Appropriate complexity level — code that solves the problem and no more
- Test suites that test behaviour rather than implementation
- Clear control flow with early returns and guard clauses
- Constants and enums used instead of magic literals

This section is not a courtesy — it is a calibration signal. If you cannot
find anything working well, reconsider whether your findings are calibrated
correctly. Real codebases have strengths.
