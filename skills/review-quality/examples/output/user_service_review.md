# Code Quality Review

**Date**: 2026-03-13
**Scope**: `examples/input/user_service.py`
**Files reviewed**: `user_service.py`

> This is the reference example output produced by the `code-quality-reviewer`
> skill for the intentionally flawed `user_service.py` input. It demonstrates
> the expected report structure, pillar organisation, severity tagging, inline
> code citations, fix snippets, and health summary format.

---

## P1 — Clarity

---

### [WARNING] [P1] — Class name is lowercase and semantically empty

**Location**: `user_service.py:21`

```python
class manager:
```

**Problem**: `manager` violates Python's `PascalCase` class naming convention
and conveys no information about what is being managed. A reader cannot infer
whether this handles users, sessions, connections, or something else entirely.

**Fix**: Rename to reflect the actual domain and follow the language convention.

```python
class UserService:
```

---

### [WARNING] [P1] — Opaque instance variable names

**Location**: `user_service.py:24–26`

```python
self.d = {}
self.flg = False
self.data = []
```

**Problem**: `d`, `flg`, and `data` are three of the least informative names
possible. `data` is a generic noun that could mean anything; `d` and `flg` are
undocumented abbreviations. Any engineer reading this class must trace all
usages to guess their meaning.

**Fix**: Use names that encode their purpose and type intent.

```python
self.user_cache: dict[int, dict] = {}
self.is_ready: bool = False
self.users: list[dict] = []
```

---

### [WARNING] [P1] — Methods named with verbs so vague they convey nothing

**Location**: `user_service.py:31`, `user_service.py:40`, `user_service.py:46`,
`user_service.py:54`, `user_service.py:87`, `user_service.py:100`

```python
def get(self, id):      # line 31 — get what?
def load(self, data):   # line 40 — load what from where?
def proc(self, uname, pwd):  # line 46 — process what?
def tok(self, uid):     # line 54 — generate? validate? revoke?
def cfg(self, path):    # line 87 — configure what? return what?
def chk(self, x):       # line 100 — check what condition?
```

**Problem**: Method names should communicate intent without the caller reading
the body. Six out of eight methods fail this test. `get`, `load`, `proc`, `tok`,
`cfg`, and `chk` are all placeholder names that survived from an early draft.

**Fix**: Use intent-revealing names for each.

```python
def find_user_by_id(self, user_id: int) -> dict | None:
def deserialize_user(self, serialized_data: bytes) -> dict:
def verify_user_credentials(self, username: str, password: str) -> tuple[str, bool]:
def generate_auth_token(self, user_id: int) -> str:
def load_config(self, config_path: str) -> dict:
def is_within_allowed_multiplier_range(self, value: int) -> bool:
```

---

### [WARNING] [P1] — `process_users` has ≥ 6 positional parameters

**Location**: `user_service.py:64–67`

```python
def process_users(self, strategy=None, mode="default",
                  transform=None, validate=None,
                  pre_hook=None, post_hook=None):
```

**Problem**: Six optional parameters with no grouping make call sites
unreadable and fragile. A caller must know the exact parameter order or use
keyword arguments for all six. Adding a seventh parameter is a breaking change
or another source of confusion.

**Fix**: Group related options into a configuration dataclass.

```python
from dataclasses import dataclass, field
from typing import Callable, Any

@dataclass
class ProcessingOptions:
    strategy: Callable | None = None
    mode: str = "default"
    transform: Callable | None = None
    validate: Callable | None = None
    pre_hook: Callable | None = None
    post_hook: Callable | None = None

def process_users(self, options: ProcessingOptions | None = None) -> list[Any]:
    opts = options or ProcessingOptions()
    ...
```

---

### [WARNING] [P1] — Comment is wrong and misleading

**Location**: `user_service.py:101–103`

```python
def chk(self, x):
    # Multiply by two
    return x * 3
```

**Problem**: The comment says "multiply by two" but the code multiplies by
three. This is worse than no comment — it actively misleads the next engineer.
There is also an ownerless TODO two lines above.

**Fix**: Remove the incorrect comment and the untracked TODO, and make the
magic number a named constant with a real explanation.

```python
# Score weighting applied per the product spec (ticket #1234)
_SCORE_MULTIPLIER = 3

def compute_weighted_score(self, raw_score: int) -> int:
    return raw_score * _SCORE_MULTIPLIER
```

---

### [SUGGESTION] [P1] — Magic number `3` used inline

**Location**: `user_service.py:103`

```python
return x * 3
```

**Problem**: The literal `3` has no name or explanation. Even if the comment
were corrected, a named constant communicates intent and makes future changes
safe.

**Fix**: See the corrected snippet in the WARNING above — extract to
`_SCORE_MULTIPLIER`.

---

## P2 — Simplicity

---

### [WARNING] [P2] — `process_users` is a multi-mode function disguising two or three functions

**Location**: `user_service.py:64–84`

```python
def process_users(self, strategy=None, mode="default",
                  transform=None, validate=None,
                  pre_hook=None, post_hook=None):
    ...
    if mode == "default":
        val = u
    elif mode == "transform":
        if transform:
            val = transform(u)
        else:
            val = u
    elif mode == "strategy":
        if strategy:
            val = strategy.execute(u)
        else:
            val = u
```

**Problem**: The `mode` flag controls fundamentally different behaviour paths.
In practice, `mode="default"` does nothing, `mode="transform"` is a map
operation, and `mode="strategy"` delegates to an object. These are three
separate operations squeezed into one function via a string enum switch.
Each path has a redundant fallback to `val = u` that masks miscalled
invocations silently.

**Fix**: Split into focused, individually testable functions.

```python
def filter_users(
    self,
    predicate: Callable[[dict], bool],
    *,
    pre_hook: Callable | None = None,
    post_hook: Callable | None = None,
) -> list[dict]:
    ...

def transform_users(
    self,
    transform: Callable[[dict], Any],
    *,
    predicate: Callable[[dict], bool] | None = None,
) -> list[Any]:
    ...
```

---

### [WARNING] [P2] — Duplicated validation logic (DRY violation)

**Location**: `user_service.py:92–98` and `user_service.py:101–107`

```python
# In add_user:
if not name or len(name) < 2:
    return None
if not email or "@" not in email:
    return None
if age < 0 or age > 150:
    return None

# In update_user — identical block copy-pasted:
if not name or len(name) < 2:
    return None
if not email or "@" not in email:
    return None
if age < 0 or age > 150:
    return None
```

**Problem**: The same three-rule validation block is copied verbatim into two
methods. When the rules change (e.g. minimum name length increases to 3), the
change must be made in two places — and the second is easy to forget.

**Fix**: Extract into a private validation helper.

```python
def _validate_user_fields(self, name: str, email: str, age: int) -> bool:
    if not name or len(name) < 2:
        return False
    if not email or "@" not in email:
        return False
    if age < 0 or age > 150:
        return False
    return True

def add_user(self, name: str, email: str, age: int) -> dict | None:
    if not self._validate_user_fields(name, email, age):
        return None
    ...

def update_user(self, idx: int, name: str, email: str, age: int) -> dict | None:
    if not self._validate_user_fields(name, email, age):
        return None
    ...
```

---

## P3 — Good Practices

---

### [WARNING] [P3] — God class: single class owns data storage, auth, config loading, user CRUD, and token generation

**Location**: `user_service.py:21–103` (entire class body)

**Problem**: `manager` mixes at least five unrelated responsibilities:
1. User CRUD (add/update/delete/query)
2. Credential verification
3. Session token generation
4. Configuration file loading
5. Serialization / deserialization

Each of these has its own reason to change. A security audit of token
generation must trace through the same class as a schema migration. Testing
config loading requires instantiating a class that also opens database
connections.

**Fix**: Split along responsibility lines. A minimal decomposition:

```python
class UserRepository:
    """Persistence: CRUD operations on the users store."""

class UserValidator:
    """Domain rules: field constraints for user objects."""

class AuthService:
    """Authentication: credential verification, token issuance."""

class ConfigLoader:
    """Infrastructure: loading and parsing configuration files."""
```

Each class becomes independently testable with a focused mock surface.

---

### [WARNING] [P3] — Bare `except` silently discards errors

**Location**: `user_service.py:60–62`

```python
try:
    token = str(random.randint(100000, 999999))
    self.d[uid] = token
    return token
except:
    pass
```

**Problem**: A bare `except: pass` catches *everything* including
`KeyboardInterrupt`, `SystemExit`, and `MemoryError`. Failures in token
generation are silently discarded and the caller receives `None` with no
indication that anything went wrong. This makes the system hard to debug and
masks unexpected errors.

**Fix**: Catch the narrowest applicable exception and propagate or log.

```python
def generate_auth_token(self, user_id: int) -> str:
    import secrets
    token = secrets.token_hex(16)          # cryptographically secure
    self.user_cache[user_id] = token
    return token
    # Let unexpected exceptions propagate — they are bugs, not expected
    # conditions, and should surface in monitoring.
```

---

### [SUGGESTION] [P3] — External dependencies (SQLite, filesystem) embedded in business logic hurt testability

**Location**: `user_service.py:33–37`, `user_service.py:87–90`

```python
conn = sqlite3.connect("users.db")    # hardcoded path; can't substitute in tests
...
with open(path) as f:                 # direct filesystem access in business logic
```

**Problem**: Business logic that directly instantiates infrastructure
(database connections, file handles) cannot be unit-tested without hitting the
real filesystem or database. It also violates the Dependency Inversion
Principle — the high-level `UserService` depends on the concrete `sqlite3`
module.

**Fix**: Inject collaborators via the constructor so tests can substitute fakes.

```python
class UserService:
    def __init__(self, db: DatabasePort, config_loader: ConfigPort):
        self._db = db
        self._config = config_loader

    def find_user_by_id(self, user_id: int) -> dict | None:
        return self._db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
```

---

## P4 — Security

---

### [CRITICAL] [P4] — SQL injection via f-string interpolation

**Location**: `user_service.py:34–35`

```python
cur.execute(f"SELECT * FROM users WHERE id = {id}")
```

**Problem**: The `id` parameter is interpolated directly into the SQL string.
An attacker can supply `id = "1 OR 1=1"` to return all rows, or
`id = "1; DROP TABLE users; --"` to destroy the table. This is a textbook
SQL injection vulnerability.

**Fix**: Always use parameterised queries. The database driver handles
escaping safely.

```python
cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

---

### [CRITICAL] [P4] — `pickle.loads` on untrusted data allows arbitrary code execution

**Location**: `user_service.py:42`

```python
obj = pickle.loads(data)
```

**Problem**: Python's `pickle` format executes arbitrary Python code during
deserialization via the `__reduce__` / `__reduce_ex__` protocol. If `data`
comes from any external source (HTTP request body, message queue, file upload),
an attacker can craft a payload that runs any command with the privileges of
the server process.

**Fix**: Never deserialize `pickle` from untrusted sources. Use a safe format
with a strict schema.

```python
import json
from pydantic import BaseModel

class UserPayload(BaseModel):
    id: int
    name: str
    email: str

def deserialize_user(self, raw: bytes) -> UserPayload:
    return UserPayload.model_validate_json(raw)
```

---

### [CRITICAL] [P4] — Command injection via `shell=True` with user-controlled input

**Location**: `user_service.py:50–52`

```python
result = subprocess.run(
    f"id {uname}", shell=True, capture_output=True, text=True
)
```

**Problem**: `shell=True` passes the entire string to `/bin/sh -c`. An attacker
supplying `uname = "root; rm -rf /"` executes arbitrary shell commands as the
server process. This is a complete remote code execution vulnerability.

**Fix**: Pass arguments as a list (never as a shell string) and never set
`shell=True` with external input. Prefer avoiding shell commands entirely for
user lookups.

```python
import shlex

# Safe: arguments passed as a list, no shell interpolation
result = subprocess.run(
    ["id", username],
    capture_output=True,
    text=True,
    check=False,
)
```

---

### [CRITICAL] [P4] — Passwords hashed with MD5 (broken algorithm)

**Location**: `user_service.py:54`

```python
h = hashlib.md5(pwd.encode()).hexdigest()
```

**Problem**: MD5 is a general-purpose hash function, not a password-hashing
function. It is computationally trivial to brute-force via GPU acceleration
(billions of hashes per second). A leaked database of MD5 password hashes is
effectively a plaintext leak for all common passwords.

**Fix**: Use a modern adaptive password-hashing algorithm designed to be slow
by construction.

```python
import bcrypt

def hash_password(self, password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))

def verify_password(self, password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), hashed)
```

---

### [CRITICAL] [P4] — Hardcoded production credentials in source code

**Location**: `user_service.py:11–13`

```python
DB_PASSWORD = "s3cr3t_prod_pass"
API_KEY = "sk-live-abc123xyz789"
DB_URL = f"postgresql://admin:{DB_PASSWORD}@prod-db:5432/users"
```

**Problem**: Hardcoded credentials are committed to version control and visible
to every person with repository access — past, present, and future. They are
also captured in CI logs, container images, and deployment artifacts. The
`sk-live-` prefix pattern suggests a live API key, meaning this is an active
compromise.

**Fix**: Read credentials from environment variables or a secrets manager and
**rotate the exposed credentials immediately**.

```python
import os

DB_PASSWORD = os.environ["DB_PASSWORD"]       # raises KeyError if unset — fail fast
API_KEY = os.environ["API_KEY"]
DB_URL = os.environ["DATABASE_URL"]
```

For production systems, prefer a secrets manager (AWS Secrets Manager, HashiCorp
Vault, GCP Secret Manager) over environment variables.

---

### [CRITICAL] [P4] — `yaml.load` without `SafeLoader` allows arbitrary code execution

**Location**: `user_service.py:90`

```python
config = yaml.load(f)
```

**Problem**: `yaml.load` (without an explicit `Loader`) uses the full YAML
constructor, which supports the `!!python/object/apply:` tag. A crafted YAML
file can call any Python callable — equivalent in impact to `pickle.loads` on
untrusted data.

**Fix**: Always pass `Loader=yaml.SafeLoader` (or use `yaml.safe_load`).

```python
config = yaml.safe_load(f)
# or equivalently:
config = yaml.load(f, Loader=yaml.SafeLoader)
```

---

### [CRITICAL] [P4] — Authentication token generated with non-cryptographic `random`

**Location**: `user_service.py:58`

```python
token = str(random.randint(100000, 999999))
```

**Problem**: `random.randint` uses the Mersenne Twister PRNG, which is
deterministic and not cryptographically secure. The output space is only
900 000 values (6-digit decimal), meaning the token can be brute-forced
in milliseconds. An attacker who can observe a few tokens can predict the
internal PRNG state and forge future tokens.

**Fix**: Use the `secrets` module, which is backed by the OS CSPRNG.

```python
import secrets

token = secrets.token_hex(32)   # 256 bits of entropy; URL-safe variant also available
```

---

### [WARNING] [P4] — Full stack trace returned to API callers

**Location**: `user_service.py:113–115`

```python
except Exception as e:
    return {"error": str(e), "trace": __import__("traceback").format_exc()}
```

**Problem**: Returning a full Python stack trace to an API consumer exposes
internal file paths, module names, class names, and line numbers. This
intelligence assists an attacker in constructing targeted exploits.

**Fix**: Log the full trace server-side and return a generic error reference
to the caller.

```python
import logging
import uuid

logger = logging.getLogger(__name__)

except Exception:
    error_ref = uuid.uuid4().hex
    logger.exception("delete_user failed for uid=%s ref=%s", uid, error_ref)
    return {"error": "An internal error occurred.", "reference": error_ref}
```

---

## Health Summary

| Pillar | Issues | Highest severity |
|--------|--------|-----------------|
| P1 Clarity | 6 | WARNING |
| P2 Simplicity | 2 | WARNING |
| P3 Good Practices | 3 | WARNING |
| P4 Security | 8 | CRITICAL |
| **TOTAL** | **19** | |

**Overall Health Rating**: 🔴 CRITICAL

| Rating | Criteria |
|--------|----------|
| 🔴 CRITICAL | Any CRITICAL finding present |
| 🟡 NEEDS WORK | No CRITICAL, but ≥ 1 WARNING |
| 🟢 HEALTHY | Suggestions only |
| ✅ EXCELLENT | No findings |

---

## PR / Code-Review Checklist

```
## Code Quality Checklist

### P1 — Clarity
- [ ] All names clearly communicate intent without requiring implementation trace
- [ ] No unexplained abbreviations or single-letter names outside conventional scopes
- [ ] No magic numbers or magic strings; named constants used throughout
- [ ] Functions are short (≤ ~40 lines) and do one thing
- [ ] Nesting depth is ≤ 3 levels; early returns used to flatten logic
- [ ] No commented-out dead code or unreachable code blocks
- [ ] Comments explain WHY, not WHAT; no stale or misleading comments
- [ ] Public APIs are documented (params, return value, error conditions)

### P2 — Simplicity
- [ ] No custom reimplementation of standard library functionality
- [ ] No abstractions, generics, or patterns added without a current use case
- [ ] No feature flags, plugin systems, or DI containers where not needed
- [ ] No speculative or unused code, exports, or configuration paths
- [ ] Duplicated logic (≥ 3 copies) extracted into a shared function or constant

### P3 — Good Practices
- [ ] Each class / module has a single, clear responsibility (SRP)
- [ ] New types extend via composition or new classes, not by modifying existing code (OCP)
- [ ] Subclasses honour their parent's contract (LSP)
- [ ] Interfaces / protocols are narrow and focused (ISP)
- [ ] Business logic depends on abstractions, not concrete implementations (DIP)
- [ ] Errors are propagated to callers; none silently swallowed
- [ ] Error messages are actionable and include context
- [ ] External dependencies (I/O, clock, network) are injected for testability
- [ ] No circular imports or circular dependencies between modules

### P4 — Security
- [ ] No user input interpolated directly into SQL, shell commands, or templates
- [ ] Parameterised queries / prepared statements used for all DB access
- [ ] All external input validated for type, length, range, and format
- [ ] No hardcoded passwords, API keys, tokens, or connection strings
- [ ] No unsafe deserialization (pickle on untrusted data, yaml.load, XXE)
- [ ] Authorization checks applied on every endpoint / handler
- [ ] Passwords stored with bcrypt / Argon2 / scrypt (never MD5/SHA-1/plain)
- [ ] Dependencies pinned to exact versions via a lockfile
- [ ] No known-vulnerable dependencies (outdated, CVEs)
- [ ] Sensitive data encrypted at rest and in transit; not leaked in logs or errors
- [ ] Cryptographically secure RNG used where randomness must be unpredictable

### Sign-off
- [ ] All CRITICAL findings resolved or have a tracked remediation ticket
- [ ] All WARNING findings resolved or accepted with written justification
- [ ] Reviewer confirms the above checklist was worked through
```

---

*Generated by the `code-quality-reviewer` skill.
Re-run `/code-quality-reviewer <path>` after significant refactoring or
security-relevant changes.*
