"""
User service — intentionally contains issues across all four review pillars.
Used as the reference example for the code-quality-reviewer skill.
"""

import pickle
import subprocess
import sqlite3
import yaml
import hashlib
import random

# ── Hardcoded secrets (P4) ──────────────────────────────────────────
DB_PASSWORD = "s3cr3t_prod_pass"
API_KEY = "sk-live-abc123xyz789"

DB_URL = f"postgresql://admin:{DB_PASSWORD}@prod-db:5432/users"


# ── God class (P3 / P1) ─────────────────────────────────────────────
class manager:                         # P1: not PascalCase; name is generic
    """Manages everything."""

    def __init__(self):
        self.d = {}                    # P1: single-letter, opaque name
        self.flg = False               # P1: abbreviation with no clear meaning
        self.data = []                 # P1: generic name

    # ── SQL injection (P4) ──────────────────────────────────────────
    def get(self, id):                 # P1: 'get' says nothing; 'id' is vague
        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        # P4: user input interpolated directly into SQL query
        cur.execute(f"SELECT * FROM users WHERE id = {id}")
        row = cur.fetchone()
        conn.close()
        return row

    # ── Unsafe deserialization (P4) ─────────────────────────────────
    def load(self, data):              # P1: 'load' — load what?
        # P4: pickle.loads on untrusted data allows arbitrary code execution
        obj = pickle.loads(data)
        self.d[obj["id"]] = obj
        return obj

    # ── Shell injection + weak password hashing (P4) ────────────────
    def proc(self, uname, pwd):        # P1: abbreviated method and param names
        # P4: shell=True with user-controlled input — command injection
        result = subprocess.run(
            f"id {uname}", shell=True, capture_output=True, text=True
        )
        # P4: MD5 is cryptographically broken for password storage
        h = hashlib.md5(pwd.encode()).hexdigest()
        return result.stdout, h

    # ── Silenced errors + non-cryptographic random token (P3 / P4) ──
    def tok(self, uid):                # P1: abbreviation, unclear semantics
        try:
            # P4: random.randint is not cryptographically secure
            token = str(random.randint(100000, 999999))
            self.d[uid] = token
            return token
        except:                        # P3: bare except swallows all errors
            pass                       # P3: error silently discarded

    # ── Premature abstraction: strategy for a single use-case (P2) ──
    def process_users(self, strategy=None, mode="default",  # P2 / P1
                      transform=None, validate=None,
                      pre_hook=None, post_hook=None):       # P1: ≥5 params
        results = []
        for u in self.data:
            if pre_hook:
                pre_hook(u)
            if validate:
                if not validate(u):
                    continue
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
            else:
                val = u
            results.append(val)
            if post_hook:
                post_hook(val)
        return results

    # ── Unsafe YAML load (P4) ────────────────────────────────────────
    def cfg(self, path):               # P1: 'cfg' — configure what? load what?
        with open(path) as f:
            # P4: yaml.load without SafeLoader allows arbitrary Python execution
            config = yaml.load(f)
        return config

    # ── Duplicated validation logic (P2 / P3) ───────────────────────
    def add_user(self, name, email, age):
        if not name or len(name) < 2:
            return None
        if not email or "@" not in email:
            return None
        if age < 0 or age > 150:
            return None
        self.data.append({"name": name, "email": email, "age": age})

    def update_user(self, idx, name, email, age):
        # P2/P3: exact same validation copy-pasted rather than extracted
        if not name or len(name) < 2:
            return None
        if not email or "@" not in email:
            return None
        if age < 0 or age > 150:
            return None
        self.data[idx] = {"name": name, "email": email, "age": age}

    # ── Stack trace returned to caller (P4) ─────────────────────────
    def delete_user(self, uid, req):
        # P4: full stack trace exposed to the API consumer
        try:
            del self.d[uid]
        except Exception as e:
            return {"error": str(e), "trace": __import__("traceback").format_exc()}

    # ── Misleading comment + magic numbers (P1 / P1) ────────────────
    def chk(self, x):                  # P1: 'chk' — check what?
        # Multiply by two                  # P1: comment restates the obvious
        # TODO: fix this properly          # P1: TODO with no ticket or owner
        return x * 3                   # P1: magic number; comment says 2, code does 3
