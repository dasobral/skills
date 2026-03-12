# cpp-realtime-reviewer skill

Structured code review for production C++ targeting real-time embedded,
cryptographic, and secure-networked systems — QKD, QRNG, and satellite-ground
communication links.

---

## What it does

Reviews C++ source across five safety-critical domains and produces a
severity-tagged report with inline-annotated code snippets and a summary
scorecard.

| Domain | What is checked |
|--------|----------------|
| **D1 Thread Safety** | Data races, TOCTOU, missing synchronisation, lock ordering violations |
| **D2 Synchronisation** | Mutex misuse, spurious wake-ups, condvar protocol, atomic ordering semantics |
| **D3 RAII / Ownership** | Raw `new`/`delete`, unowned handles, exception-safety, smart pointer misuse |
| **D4 Latency / Hot Path** | Blocking syscalls, dynamic allocation, lock contention, I/O in real-time paths |
| **D5 Logging Safety** | Unsynchronised logs, blocking log calls, secrets/key material in log output |

Every finding is tagged **CRITICAL**, **WARNING**, or **SUGGESTION** and
includes the defective code, the problem explanation, and a corrected snippet.

---

## File tree

```
cpp-realtime-reviewer/
├── SKILL.md                              # Skill definition and agent instructions
├── README.md                             # This file
├── references/
│   ├── review-checklist.md               # Full per-domain defect checklist
│   └── severity-guide.md                 # Severity classification rules
├── templates/
│   └── review-report.md                  # Structured report output template
└── examples/
    ├── input/
    │   └── websocket_handler.cpp         # Mock concurrent WebSocket handler (with defects)
    └── output/
        └── websocket_handler_review.md   # Example review output for the above file
```

---

## Installation

```bash
# Project-level (recommended — checked in with the project)
cp -r cpp-realtime-reviewer/ /path/to/project/.claude/skills/

# Personal (available across all projects on this machine)
cp -r cpp-realtime-reviewer/ ~/.claude/skills/
```

Claude Code discovers skills automatically at session start — no restart needed.

---

## Usage

### Slash command

```
/cpp-realtime-reviewer                        # review all .cpp/.hpp/.h in the project
/cpp-realtime-reviewer src/net/ws_handler.cpp # review a specific file
/cpp-realtime-reviewer src/crypto/            # review an entire directory
```

### Natural language triggers

Claude invokes the skill automatically when you write phrases like:

- "Review this C++ file for thread safety."
- "Check for race conditions in `src/qkd/key_exchange.cpp`."
- "Audit my mutex and condvar usage."
- "Are there any blocking calls in my hot path?"
- "Check RAII correctness in this snippet."
- "Is my logging safe under concurrency?"
- "Review this for real-time correctness."
- "Audit for cryptographic safety."

### Pasted code

Paste a C++ snippet directly into the chat and ask for a review — the skill
analyses the snippet as `snippet:N` line references.

---

## Output format

```
## C++ Real-Time Review — <filename>
Date: <ISO date>

### [CRITICAL] D1 — Data race on `session_map_`
File: ws_handler.cpp:87–92
...
Fix:
  std::lock_guard<std::mutex> lk(session_map_mutex_);

---

## Summary Scorecard
| Domain            | Issues | Highest severity |
|-------------------|--------|-----------------|
| D1 Thread Safety  |   2    | CRITICAL         |
...
Overall Risk Rating: 🔴 HIGH
```

---

## Severity at a glance

| Tag | Meaning |
|-----|---------|
| **CRITICAL** | Undefined behaviour, data corruption, deadlock, key/secret exposure |
| **WARNING** | Likely bug, latency violation, or unsafe pattern in production |
| **SUGGESTION** | Better practice worth adopting; no immediate risk |

See `references/severity-guide.md` for the full classification rules.

---

## Example

The `examples/` directory contains a deliberately defective mock WebSocket
handler (`examples/input/websocket_handler.cpp`) and its annotated review
output (`examples/output/websocket_handler_review.md`). Use these to:

- Understand what the skill's output looks like before using it on real code.
- Run the skill on the example to verify the installation works:
  `/cpp-realtime-reviewer examples/input/websocket_handler.cpp`

---

## PR / code-review checklist

Every review report ends with a copy-paste checklist for use in GitHub PR
descriptions or internal code-review tools. The checklist is generated from
`templates/review-report.md`.

---

## Customising the checklist

Edit `references/review-checklist.md` to add domain-specific checks for your
project — for example, additional QKD protocol invariants, custom QRNG seeding
requirements, or proprietary FPGA/DSP latency constraints. Changes take effect
on the next invocation.
