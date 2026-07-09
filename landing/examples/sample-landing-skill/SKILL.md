---
name: sample-landing-skill
description: >
  Example skill for landing zone documentation. Copy to landing/skills/ and
  assign in registry.yaml before running skills-maintain. Not ingested from examples/.
license: MIT
---

# Sample Landing Skill

This is a template. Copy this folder to `landing/skills/<your-skill>/` and edit.

## Step 1

Follow Agent Skills format: `SKILL.md`, optional `references/`, `templates/`.

## Step 2

Add to `landing/registry.yaml`:

```yaml
assignments:
  your-skill: codecraft
```

## Step 3

Run `./bin/skills-maintain`.
