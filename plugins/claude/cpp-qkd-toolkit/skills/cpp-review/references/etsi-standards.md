# ETSI QKD Standards Reference

Reference document for the `qkd-security-engineer` skill.
Covers the standards most relevant to classical ground segment software
engineering in a QKD key management context.

---

## ETSI GS QKD 004 — Application Interface

**Full title**: Quantum Key Distribution (QKD); Application Interface

**Scope**: Defines how consuming applications request key material from a
Key Management System (KMS). This is the southbound interface of the KMS
— what applications call to get keys.

### Key abstractions

| Term | Definition |
|------|-----------|
| **QKD Application** | A consuming application that uses QKD keys (e.g., encryption engine, VPN gateway) |
| **QKD Module** | The hardware/software component managing the quantum channel |
| **KMS** | Key Management System — mediates key supply between QKD modules and applications |
| **Key stream ID** | Unique identifier for a logical key stream between two SAEs |

### Key supply model (GS QKD 004)
- The application requests a key by specifying the remote peer's SAE ID and
  the required key length.
- The KMS returns the key material and a key identifier.
- The same key (by identifier) is delivered to both the local and remote
  application — they must not request it independently.

---

## ETSI GS QKD 014 — Key Delivery API (REST)

**Full title**: Quantum Key Distribution (QKD); Protocol and data format
of REST-based key delivery API

**Scope**: Defines the REST HTTP API for key supply between QKD nodes and
consuming applications. This is the interface most directly implemented in
C++ ground segment software.

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/keys/{SAE_ID}/enc_keys` | GET | Request keys for encryption (initiating peer) |
| `/api/v1/keys/{SAE_ID}/dec_keys` | POST | Request keys for decryption (responding peer) using key IDs |
| `/api/v1/keys/{SAE_ID}/status` | GET | Query KMS status and available key material |

### Request parameters (`enc_keys`)

| Parameter | Type | Description |
|-----------|------|-------------|
| `number` | integer | Number of keys requested |
| `size` | integer | Key size in bits |
| `additional_slave_SAE_IDs` | array | Additional SAE IDs if multicast key supply needed |
| `extension_mandatory` | array | Mandatory extension parameters |
| `extension_optional` | array | Optional extension parameters |

### Response schema (`enc_keys`)

```json
{
  "keys": [
    {
      "key_ID": "<UUID>",
      "key": "<Base64-encoded key material>"
    }
  ],
  "key_container_extension": {}
}
```

> **Security note**: The `key` field contains raw key material in Base64.
> This response must be handled over TLS only, stored in memory (not logged),
> and the key bytes zeroized immediately after use.

### Error codes

| HTTP code | Meaning |
|-----------|---------|
| 200 | Keys returned successfully |
| 400 | Bad request (invalid parameters) |
| 401 | Unauthorised (authentication required) |
| 503 | Service unavailable (insufficient key material) |

---

## EuroQCI Architecture

**EuroQCI**: European Quantum Communication Infrastructure

A European Commission programme to deploy a pan-European QKD network connecting
member states, with ESTEC / ESA as a key technical participant.

### Architecture tiers

```
Tier 1: Terrestrial QKD links (fibre-based)
  ↕  QKD nodes at national sites
Tier 2: Satellite QKD links (for cross-border long distances)
  ↕  Ground stations with optical QKD receivers
Tier 3: Classical ground segment
  ↕  KMS nodes at each site
  ↕  Classical networks (TLS-authenticated) interconnecting KMS nodes
Applications
  ↕  ETSI GS QKD 014 REST API
  End-to-end secure services (government, critical infrastructure)
```

### Key relay security model
In multi-hop topologies (A → relay → B):
- Each relay node is a **trusted third party** — it decrypts and re-encrypts
  key material at each hop.
- The end-to-end security guarantee is **only as strong as the weakest relay**.
- Each relay-to-relay link must be independently authenticated.
- A compromised relay exposes all key material transiting through it.

### Trust hierarchy
- Each KMS-to-application link authenticated with separately managed keys
  (not the QKD keys being distributed — circular dependency risk).
- Each KMS-to-KMS link independently authenticated.
- No single KMS failure should compromise the entire network — design for
  partial trust and alert propagation.

---

## Classical Channel Authentication — Key Requirements

The classical channel (sifting, error correction, privacy amplification) must
be **independently authenticated**. QKD does not secure it.

| Requirement | Implementation |
|-------------|---------------|
| Authentication primitive | HMAC-SHA256 or AEAD (e.g., AES-GCM) with pre-shared auth key |
| Replay protection | Monotonically increasing sequence number in every message |
| Key for authentication | Pre-shared key or previously distilled QKD key (never the current session key) |
| Failure action | Authentication failure → session abort + operator alert |

---

## QBER Thresholds

| Protocol | Typical abort threshold | Significance |
|----------|------------------------|--------------|
| BB84 | ~11% | Above this, eavesdropping or equipment fault assumed |
| E91 | Protocol-specific | Violation of Bell inequalities indicates eavesdropping |

> **Hard rule**: Any code that continues key distribution after a QBER
> threshold violation is a **CRITICAL** defect. No degraded mode, no fallback.
> Abort the session and alert the operator.
