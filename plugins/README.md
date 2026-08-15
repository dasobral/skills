# Plugins

Each directory is an [Agent Plugins 1.0.0](https://agent-plugins.org) package:

```text
plugins/codecraft/
├── plugin.json          # portable manifest
└── skills/
    └── analyze-codebase → ../../../skills/analyze-codebase
```

Skill bodies are not copied. `plugin.json` is the portable contract for Cursor, Codex, Copilot, VS Code, and Kiro. Cursor/Codex agents, hooks, and rules stay in `adapters/` and are installed with `./bin/skills-install`.

Regenerate with `./bin/skills-export export`.
