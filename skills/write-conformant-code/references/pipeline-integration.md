# Pipeline Integration

Documents how `style-conformant-coder` connects to the other two skills in
the three-skill pipeline.

---

## The Canonical Three-Skill Workflow

```
┌──────────────────────┐
│   codebase-analyst   │  /analyze-codebase [path]
│                      │  Analyses the project across 16 dimensions.
└──────────┬───────────┘
           │ writes
           ▼
┌──────────────────────────────┐
│     CODING_REQUIREMENTS.md   │  Authoritative style and convention file.
│  (.claude/ or docs/ or root) │  Loaded automatically by subsequent skills.
└──────────┬───────────────────┘
           │ read by
           ▼
┌──────────────────────────┐
│  style-conformant-coder  │  /style-conformant-coder
│                          │  Writes code that matches the profile exactly.
└──────────┬───────────────┘
           │ output fed into
           ▼
┌──────────────────────────┐
│  code-quality-reviewer   │  /code-quality-reviewer
│                          │  Validates style conformance before delivery.
└──────────────────────────┘
```

For C++ targeting real-time or embedded systems, extend the pipeline with
one additional pass:

```
style-conformant-coder
    → code-quality-reviewer
        → cpp-realtime-reviewer   (concurrency and latency domain pass)
```

---

## Invoking Each Skill

### codebase-analyst

```
/analyze-codebase
/analyze-codebase src/
/analyze-codebase src/payments/
```

Natural language triggers:
- "Analyze the codebase and capture its conventions"
- "Document coding standards for this project"
- "Extract the style from this codebase"

**Output:** `CODING_REQUIREMENTS.md` written to `.claude/`, `docs/`, or the
project root (first available location). Also writes `.claude/instructions.md`
as an auto-load pointer and updates `CLAUDE.md`.

### style-conformant-coder

```
/style-conformant-coder
```

Natural language triggers (all auto-trigger this skill):
- "Write a function that…"
- "Implement X for this codebase"
- "Write this in my style"
- "Solve this in clean idiomatic [language]"
- Any interview or algorithmic problem
- Any code that should fit an existing codebase

**Input consumed:** `CODING_REQUIREMENTS.md` (loaded automatically), or
`code-quality-reviewer` output present in the conversation.

### code-quality-reviewer

```
/code-quality-reviewer
/code-quality-reviewer src/payments/processor.py
```

Natural language triggers:
- "Review this code"
- "Check code quality"
- "Audit for style violations"
- Pasting code and asking for a review

**Input consumed:** Source files from the working directory, a provided path,
or a pasted code block.

---

## What CODING_REQUIREMENTS.md Contains

`codebase-analyst` produces a prescriptive, imperative document with these
sections (based on its 16-dimension analysis):

| Section | Contents |
|---------|----------|
| Naming conventions | Rules for variables, functions, types, constants per language |
| Formatting | Indentation, line length, brace style, blank lines |
| Module/file layout | How code is organised across files and directories |
| Import conventions | Ordering, grouping, aliasing |
| Type annotation expectations | When and how types are annotated |
| Error handling | Idiom in use (exceptions, result types, sentinel values) |
| Async patterns | How concurrency is expressed |
| Test conventions | Framework, file layout, naming, parametrisation |
| Logging and observability | Log levels, structured vs. unstructured |
| Documentation and comments | Docstring format, inline comment rules |
| Dependency management | Package manager, import hygiene |
| Anti-patterns observed | Explicit list of patterns found in the codebase to avoid |
| Architectural patterns | DI, layering, service boundaries |
| Performance conventions | Caching, lazy evaluation, profiling hints |
| Security practices | Input validation, secret handling |
| Tooling | Linter, formatter, type-checker configuration in use |

Each rule is written as an actionable imperative with a real file:line
reference from the codebase as supporting evidence.

---

## Chaining code-quality-reviewer After style-conformant-coder

After `style-conformant-coder` produces code, pipe it through
`code-quality-reviewer` to catch style violations before delivery:

1. Copy the generated code block into a temporary file or paste it in the
   next message.
2. Invoke: `/code-quality-reviewer` (or ask "review this code for style").
3. `code-quality-reviewer` will flag `WARNING` or `SUGGESTION` findings for
   any conventions the generated code violated.
4. Feed findings back to `style-conformant-coder` for a targeted revision if
   needed.

This loop is most valuable on large implementations or when the style profile
is dense. For short functions, a single pass is usually sufficient.

---

## When to Re-Run codebase-analyst

Re-run `/analyze-codebase` when any of the following occur:

- **New project or codebase** — no `CODING_REQUIREMENTS.md` exists yet.
- **Major refactor** — the architectural layer structure or dominant patterns
  have changed significantly.
- **New language added** — the existing profile covers Python but the project
  now also has TypeScript services; run on the new directories.
- **Conventions updated** — the team has consciously changed a rule (e.g.,
  migrated from exceptions to result types).
- **Profile is stale** — the current `CODING_REQUIREMENTS.md` was generated
  more than a few months ago and the codebase has evolved.
- **Inconsistent output** — `code-quality-reviewer` is flagging generated
  code for patterns that the profile does not mention, indicating the profile
  is incomplete.

---

## The cpp-realtime-reviewer Extension

For C++ code targeting real-time, embedded, or networked systems, add a
third review pass:

```
/cpp-realtime-reviewer
/cpp-realtime-reviewer src/comms/serial_driver.cpp
```

This pass checks:
- Thread safety, mutex and atomic correctness, condvar usage.
- RAII and resource ownership under interrupt/signal conditions.
- Blocking calls in interrupt service routines or hard-real-time loops.
- Latency bottlenecks: heap allocation, `std::endl`, lock contention in hot
  paths.
- Concurrency-safe logging practices.
- QKD/QRNG and cryptographic constant-time idioms (where applicable).

Run this pass **after** `code-quality-reviewer`, not instead of it.
`code-quality-reviewer` covers general code health; `cpp-realtime-reviewer`
covers domain-specific real-time and embedded correctness that general
review tools miss.
