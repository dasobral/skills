# Agent STE Instruction Block Template

Copy and fill every field. Use `NONE`, `N/A`, or `UNKNOWN` explicitly — never omit a field silently.

```text
## AGENT-STE INSTRUCTION
SCHEMA: agent-ste/0.1
OBJECTIVE: <one sentence, one primary objective>

### ENTITIES
| ID | Type | Name / Path | Notes |
|----|------|-------------|-------|
| <ID> | actor\|system\|file\|service\|artifact\|secret | <stable name> | |

### GLOSSARY
| Term | Allowed meaning in this instruction | Banned synonyms |
|------|--------------------------------------|-----------------|
| <term> | <one meaning> | <list> |

### SCOPE
IN: <what may change or be read>
OUT: <what must not change>

### ASSUMPTIONS
- <assumption> ; IF FALSE → <halt|ask|branch>

### CONSTRAINTS
- <constraint with units/limits>

### PRECONDITIONS
- <observable condition that must hold before step 1>

### INPUTS
| ID | Source | Format | Required |
|----|--------|--------|----------|
| | | | yes\|no |

### ORDERED ACTIONS
1. <ACTOR-ID> <verb> <OBJECT-ID> <qualifiers>.
2. ...
PARALLEL: <id-a> || <id-b> | NONE

### EXPECTED ARTIFACTS
| ID | Path / URI | Format | Producer step |
|----|------------|--------|---------------|

### OUTPUTS
| ID | Destination | Format |

### POSTCONDITIONS
- <observable condition after success>

### INVARIANTS
- <condition that must hold during and after>

### SUCCESS CRITERIA
- <checkable predicate with units/commands/exit codes>

### FAILURE CONDITIONS
- <predicate> → ACTION: retry <n> | abort | rollback | escalate

### VALIDATION PROCEDURE
1. <command or inspection>
2. <expected result>

### SIDE EFFECTS
- <external mutation, notification, billing, cache, etc.> | NONE

### PERMISSIONS REQUIRED
- <role, token, network, filesystem capability> | NONE

### EXTERNAL DEPENDENCIES
- <service, tool, MCP server, API> | NONE

### IDEMPOTENCY
- SAFE TO RE-RUN: yes|no
- IF RE-RUN: <behavior>

### ROLLBACK
- <exact reverse steps or NONE — <reason>>

### COMPLETION CHECKLIST
- [ ] <item>
- [ ] Agent STE checklist: references/checklist.md → all required YES
```
