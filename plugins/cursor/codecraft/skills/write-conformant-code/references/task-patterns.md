# Task Patterns

Common task types and how to handle each. Apply these patterns on top of the
loaded style profile — they govern structure and scope, not naming or formatting.

---

## Algorithmic / Interview Problems

**Scope:** A self-contained computational problem with defined input and output.

**Approach:**
- No scaffolding. No `main()`, no driver code, no example usage unless asked.
- Write the function only.
- Name the function after what it computes, not after the problem title.
- Include an explicit corner case list after the code (see Step 4 of the
  skill workflow).
- Add a complexity note — one line: `O(n log n) time, O(n) space` — after
  the contract. This is the one case where a brief complexity comment is
  expected.
- Do not add a docstring that restates the problem statement.

**Anti-patterns to avoid:**
- Printing to stdout in the body of the function.
- Returning strings like `"impossible"` when a `None` / empty result is
  more appropriate for the type.
- Premature generalisation (dynamic programming when a greedy solution is
  correct and simpler).

---

## Adding a Function to an Existing Module

**Scope:** The new function lives alongside existing code in a file you can read.

**Approach:**
- Read the target file first. Match its exact style — indentation, import
  ordering, docstring format, error idiom, naming conventions.
- Place the function where it belongs logically (grouped with related
  functions, not appended at the end arbitrarily).
- Check existing imports; add only what is not already present.
- Do not restructure, rename, or reformat unrelated code.
- Do not change the function signatures of existing functions.
- If a helper already exists in the module that does part of the job, use it.

**Anti-patterns to avoid:**
- Adding imports that duplicate existing aliases (`import numpy as np` when
  `np` is already imported).
- Introducing a different formatting style in the new function (e.g.,
  2-space indent in a 4-space file).
- Extracting private helpers into the module's public API.

---

## Implementing a Data Structure

**Scope:** A full ADT — stack, queue, trie, graph, cache, etc.

**Approach:**
- Implement the complete interface: construction, insertion, deletion,
  lookup, iteration if applicable.
- Document invariants as brief inline comments where they are not obvious
  from the names alone (e.g., `# heap property: parent ≤ children`).
- Cover error cases explicitly: operations on empty structures, out-of-bounds
  access, duplicate keys (where the semantics matter).
- Expose the minimal public surface. Internal helpers are private.
- Do not implement methods that were not asked for in the name of
  "completeness" — if the user asked for a min-heap, do not add `max()`.

**Anti-patterns to avoid:**
- Silent failure (returning `None` / `0` from an operation that should
  raise on invalid state).
- Exposing internal representation through the public API.
- Over-generalising (template/generic version when a typed version was asked
  for).

---

## Writing Tests

**Scope:** Test cases for an existing function, class, or module.

**Approach:**
- Identify the test framework in use first: `pytest`, `unittest`,
  `jest`/`vitest`, `go test`, `cargo test`, etc. Match it exactly — do not
  introduce a different framework.
- Match the file layout convention: `test_foo.py` vs. `foo_test.go` vs.
  `foo.test.ts`.
- Parametrize cases that share the same assertion logic but differ in input.
- One assertion per logical expectation — but do not split a single logical
  check into multiple `assert` calls that test sub-steps.
- No redundant assertions (do not assert both `len(result) == 1` and
  `result[0] == x` unless both are independently meaningful).
- Cover: happy path, boundary values, empty/zero inputs, invalid inputs,
  error paths.
- Test names describe the scenario, not the implementation (`test_returns_empty_list_when_input_is_empty`,
  not `test_function_1`).

**Anti-patterns to avoid:**
- Assertions on implementation details (internal state, call counts) unless
  explicitly testing a mock interaction.
- Tests that only pass when run in a specific order.
- Hard-coded paths or environment-specific values.

---

## Translating Code Between Languages

**Scope:** The user provides code in language A and asks for the equivalent in language B.

**Approach:**
- Do **not** transliterate. A line-by-line port almost always produces
  unidiomatic output.
- Understand the algorithm or data transformation first, then write it fresh
  in the target language using that language's idioms.
- Apply the full style profile for the target language.
- If the source uses a construct with no direct equivalent (e.g., Python
  generators into Go), choose the idiomatic Go alternative and note the
  semantic difference if it is material.
- Preserve the function signature semantics (inputs, outputs, error
  behaviour) even if the surface syntax changes.

**Anti-patterns to avoid:**
- Using a third-party library in the target language to paper over a
  language-level gap when a standard-library solution exists.
- Keeping the original language's naming conventions in the translated code.
- Carrying over the original language's error idiom (e.g., returning `-1`
  for error in Rust instead of `Result`).

---

## Filling in a Stub / Completing a TODO

**Scope:** A function signature or stub already exists; the body needs writing.

**Approach:**
- Read the surrounding file carefully before writing a single line.
- Do not change the function signature. If the signature is wrong, note it
  after the implementation — do not silently alter it.
- Honour the existing surrounding style exactly: same indentation, same
  comment style, same error idiom.
- If the TODO comment contains partial constraints or hints, implement them
  faithfully. If they are wrong, note that after the implementation.
- Do not add imports beyond what the stub's file already uses unless
  absolutely required.

**Anti-patterns to avoid:**
- Changing the function name, parameter names, or return type.
- Reformatting the surrounding code to match your preferences.
- Treating a `TODO: optimise later` comment as permission to write a
  complex solution.

---

## Performance-Sensitive Code

**Scope:** The user explicitly asks for a fast implementation, or the context
(tight loop, hot path, real-time constraint) makes performance important.

**Approach:**
- State the time and space complexity explicitly after the contract (one line).
- Prefer clarity over micro-optimisation unless profiling data or explicit
  constraints (e.g., "must run in < 1 ms on 1 M elements") are provided.
- Algorithmic improvements (better big-O) take priority over constant-factor
  tricks (loop unrolling, cache line tuning).
- If a simpler O(n log n) solution exists alongside a complex O(n) one,
  prefer the simpler one unless the constraint rules it out — and note the
  trade-off.
- Avoid premature pessimisation: do not use an O(n²) algorithm when O(n log n)
  is just as clear.

**Anti-patterns to avoid:**
- Sacrificing correctness for speed without documenting the trade-off.
- Using platform-specific intrinsics or SIMD without an explicit request or
  clear necessity.
- Micro-optimising before the hot path has been identified by measurement.
- "Fast" code with no corner case handling — an incorrect fast function is
  worse than a correct slow one.
