# Adapters

Platform extras only. Portable skills live in `skills/`. Agent Plugins packages live in `plugins/<family>/`.

```
adapters/<platform>/<plugin>/
  plugin.json or .*-plugin/plugin.json
  agents/ hooks/ rules/ …
  README.md
```

`skills-install cursor|codex --plugins` merges these with portable skills into install paths. Claude Code has no extras here.
