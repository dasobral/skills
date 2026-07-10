# C++ QKD Production Standards

Apply these objective constraints in QKD and defense ground-segment code:

- Never log key material, nonces, initialization vectors, or credentials.
- Document the state protected by every mutex.
- Use RAII ownership, smart pointers, and `noexcept` destructors.
- Handle reconnects and mid-message failures on every network path.
- Verify C++17 compatibility before selecting language or library features.
- Establish assets, trust boundaries, and adversary capabilities before a
  security architecture review.

Use `cpp-engineer` for implementation and `cpp-review` with the security lens
for cryptographic or protocol audits.
