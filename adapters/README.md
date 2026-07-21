# Adapters

Platform scaffolding only. Portable skills live in `core/skills/`.

```
adapters/<platform>/<plugin>/
  plugin.json or .*-plugin/plugin.json
  agents/ hooks/ rules/ …
  README.md
```

Export/install merges these with core skills into `dist/` (not committed).
