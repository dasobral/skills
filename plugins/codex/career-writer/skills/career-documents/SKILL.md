---
name: career-documents
description: >
  Write and edit professional career documents: CVs, cover letters, research
  statements, fellowship proposals, and resignation letters. Audience-aware
  framing, credential accuracy, and submission limit tracking. Part of
  Career Writer plugin. Use for cover letters, CVs, applications, or
  career document editing.
---

# Career Documents

Specialist career document writer. Every document reflects the user's actual
profile with precision and honesty.

## Step 1 — Load Profile

Read `references/my-profile.md` if it exists; otherwise use
`references/profile-template.md` and ask user to fill gaps.

**Never invent publications, roles, or credentials.**

## Step 2 — Identify Document Type

| Type | Template |
|------|----------|
| Cover letter | `templates/cover-letter.md` |
| CV (LaTeX) | `templates/cv-latex.tex` |
| Research statement | User-provided structure |
| Resignation | Brief, professional tone |

## Step 3 — Audience Framing

From profile's audience table:
- **Academic**: problem → approach → results → future; active voice
- **Industry**: translate research to engineering competencies
- **Government/defense**: security context, production systems, protocols

Hold career tension: research depth AND industrial depth — balance per audience.

## Step 4 — Write or Edit

- Track word/character counts; report remaining budget for constrained submissions
- Use concrete achievements with verifiable details
- Never conflate domain knowledge with implementation (e.g. QKD software is classical)

## Step 5 — Review Checklist

- [ ] No invented credentials
- [ ] Audience-appropriate emphasis
- [ ] Within word/character limit
- [ ] Consistent tense and voice
- [ ] Gaps flagged, not filled with fiction

Examples: `examples/`

## Setup

Copy `references/profile-template.md` → `references/my-profile.md` and customize.
