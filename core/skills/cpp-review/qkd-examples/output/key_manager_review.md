# QKD Security Engineering Review: key_manager.cpp

**Date**: 2026-03-13
**Scope**: Key manager implementation — key storage, consumption, encryption, QBER check
**Files reviewed**: `examples/input/key_manager.cpp`
**Threat model**: Dolev-Yao adversary on classical channel; key material is the
primary asset; any inter-component message may be forged or replayed.

---

## CRITICAL Findings

### [CRITICAL] [S2] — Key material logged in plaintext

**File**: `key_manager.cpp:45–48`

```cpp
for (auto b : key) {
    oss << std::hex << static_cast<int>(b);
}
std::cout << "Stored key " << key_id << ": " << oss.str() << std::endl;
```

**What is wrong**: Raw key bytes are formatted into a hex string and written
to stdout. In a production daemon, this flows into the system journal or log
files, permanently persisting the key material.

**Why it matters**: Any party with access to logs (operator, sysadmin, log
aggregation service, attacker with log access) can recover the key material.
This destroys forward secrecy and breaks the fundamental QKD security guarantee.

**Fix**:

```cpp
// Log only the non-secret key identifier — never the key value
syslog(LOG_INFO, "[KeyManager] Stored key id=%s [tid=%lu]",
       key_id.c_str(), pthread_self());
```

---

### [CRITICAL] [S2+S3] — Custom XOR cipher with no authentication

**File**: `key_manager.cpp:72–79`

```cpp
for (size_t i = 0; i < plaintext.size(); i++) {
    ciphertext[i] = plaintext[i] ^ key[i % key.size()] ^ (nonce & 0xFF);
}
```

**What is wrong**: A hand-rolled XOR cipher provides no semantic security and
absolutely no authentication. A Dolev-Yao adversary can flip arbitrary bits in
the ciphertext without detection. This is not encryption — it is obfuscation.

**Why it matters**: An authenticated adversary can forge or modify any
"encrypted" message without the receiver being able to detect the tampering,
bypassing all protocol security guarantees.

**Fix**: Use an audited AEAD library. Never roll custom crypto:

```cpp
#include <sodium.h>  // libsodium — AEAD: XSalsa20-Poly1305

// Authenticated encryption with associated data
int result = crypto_secretbox_easy(
    ciphertext.data(),
    plaintext.data(), plaintext.size(),
    nonce_bytes,    // 24-byte nonce from secure persistent counter
    key.data()      // 32-byte key
);
if (result != 0) { /* handle error */ }
```

---

### [CRITICAL] [S5] — QBER threshold not enforced

**File**: `key_manager.cpp:83–91`

```cpp
bool check_qber(double qber) {
    if (qber > 0.20) {
        std::cout << "QBER very high: " << qber << std::endl;
        return false;
    }
    return true; // Silent continuation above BB84 threshold (~11%)
}
```

**What is wrong**: The BB84 abort threshold is ~11%. This code continues key
distribution for QBER values between 11% and 20% — a range that unambiguously
indicates potential eavesdropping or equipment fault.

**Why it matters**: Continuing key distribution above the threshold distributes
keys that may be partially known to an eavesdropper, breaking the unconditional
security guarantee of QKD.

**Fix**:

```cpp
bool check_qber(double qber) {
    constexpr double BB84_ABORT_THRESHOLD = 0.11;
    if (qber > BB84_ABORT_THRESHOLD) {
        // Abort session and alert operator — no degraded mode
        syslog(LOG_CRIT,
               "[KeyManager] QBER threshold exceeded: %.4f > %.4f. "
               "Aborting session.", qber, BB84_ABORT_THRESHOLD);
        return false;  // caller must abort the QKD session immediately
    }
    return true;
}
```

---

### [CRITICAL] [S1] — Messages accepted without authentication

**File**: `key_manager.cpp:95–101`

```cpp
void process_message(const Message& msg) {
    // No authentication check
    handle_payload(msg.payload);
}
```

**What is wrong**: The `Message` struct has no HMAC or AEAD tag, and
`process_message` does not verify one. Any message arriving on the classical
channel is processed as legitimate, regardless of origin.

**Why it matters**: A Dolev-Yao adversary can forge arbitrary protocol messages
(sifting, error correction, privacy amplification) causing key synchronisation
failures, incorrect key consumption, or protocol state corruption.

**Fix**:

```cpp
// Every Message must carry an HMAC-SHA256 tag
struct AuthenticatedMessage {
    uint64_t sequence;
    std::string payload;
    std::array<uint8_t, 32> hmac_tag;  // HMAC-SHA256 over sequence + payload
};

void process_message(const AuthenticatedMessage& msg) {
    if (!verify_hmac(msg, auth_key_)) {
        syslog(LOG_ERR, "[KeyManager] Authentication failure on message seq=%lu. "
               "Aborting.", msg.sequence);
        abort_session();
        return;
    }
    if (msg.sequence <= last_seq_) {
        syslog(LOG_ERR, "[KeyManager] Replay detected: seq=%lu <= last=%lu",
               msg.sequence, last_seq_);
        abort_session();
        return;
    }
    last_seq_ = msg.sequence;
    handle_payload(msg.payload);
}
```

---

## WARNING Findings

### [WARNING] [S3] — Key buffers not zeroized on destruction

**File**: `key_manager.cpp:32–35`

```cpp
~KeyManager() {
    // keys_ destroyed here without zeroization
}
```

**Problem**: `std::map<std::string, Key>` destructor frees heap memory without
zeroing the key bytes first. Key material persists in freed heap pages, readable
via memory dump or crash analysis.

**Fix**:

```cpp
~KeyManager() {
    for (auto& [id, key] : keys_) {
        sodium_memzero(key.key_material.data(), key.key_material.size());
    }
}
```

---

### [WARNING] [S3] — Consumed key copy not zeroized by caller

**File**: `key_manager.cpp:55–61`

```cpp
auto key_copy = it->second.key_material;
it->second.consumed = true;
return key_copy;
```

**Problem**: The returned `std::vector<uint8_t>` is a heap copy of the key
material. The caller is responsible for zeroizing it after use, but there is no
contract, RAII guard, or documentation enforcing this.

**Fix**: Return a RAII wrapper that zeroizes on destruction:

```cpp
struct SecureKey {
    std::vector<uint8_t> material;
    ~SecureKey() { sodium_memzero(material.data(), material.size()); }
};
SecureKey consume_key(const std::string& key_id);
```

---

### [WARNING] [S4] — Nonce counter resets to 0 on process restart

**File**: `key_manager.cpp:16`

```cpp
static uint64_t g_nonce_counter = 0;
```

**Problem**: The nonce counter is an in-memory static variable. Every process
restart resets it to 0. If the same key is still valid after a restart, the
first encryption will reuse nonce 0 — breaking the nonce uniqueness invariant.
For AES-GCM, a single nonce reuse with the same key leaks the authentication
key and potentially plaintext.

**Fix**: Persist the nonce counter to durable storage (file, database) and
load + increment on startup. Alternatively, generate nonces from a CSPRNG
(acceptable for XSalsa20-Poly1305, which uses 192-bit nonces):

```cpp
// Using libsodium random nonce (safe for XSalsa20-Poly1305)
std::array<uint8_t, crypto_secretbox_NONCEBYTES> nonce;
randombytes_buf(nonce.data(), nonce.size());
```

---

### [WARNING] [S5] — Non-atomic key consumption

**File**: `key_manager.cpp:55–59`

```cpp
auto key_copy = it->second.key_material;  // step 1: copy
it->second.consumed = true;               // step 2: mark (race window here)
```

**Problem**: Between step 1 and step 2, another thread (or a concurrent call)
can retrieve the same key, resulting in key reuse. For a KMS, key consumption
must be atomic.

**Fix**: Use a mutex and mark the key as consumed before returning it:

```cpp
std::lock_guard<std::mutex> lock{keys_mutex_};
auto it = keys_.find(key_id);
if (it == keys_.end() || it->second.consumed) {
    throw std::runtime_error("Key unavailable: " + key_id);
}
it->second.consumed = true;  // atomic under lock
auto key_copy = it->second.key_material;
return SecureKey{std::move(key_copy)};
```

---

## Summary Table

| Domain | Issues | Highest severity |
|--------|--------|-----------------|
| S1 — Authentication Gaps | 1 | CRITICAL |
| S2 — Key Material Exposure | 2 | CRITICAL |
| S3 — Missing Zeroization | 2 | WARNING |
| S4 — Nonce / IV Reuse | 2 | CRITICAL |
| S5 — Protocol Violations | 2 | CRITICAL |
| **TOTAL** | **9** | **CRITICAL** |

**Overall Risk Rating**: 🔴 HIGH — 5 CRITICAL findings. This code must not
be used in any QKD key management context without addressing all CRITICAL
findings.

---

*Generated by the `qkd-security-engineer` skill.*
*Re-run `/qkd-security-engineer` after applying fixes.*
