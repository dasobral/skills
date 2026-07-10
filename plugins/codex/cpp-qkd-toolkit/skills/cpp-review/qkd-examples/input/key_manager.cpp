// ── key_manager.cpp ───────────────────────────────────────────────────────────
// Example QKD Key Manager with deliberate security defects for review practice.
// This is NOT production-quality code — it is an input for the
// qkd-security-engineer skill review workflow.
// ─────────────────────────────────────────────────────────────────────────────

#include <string>
#include <vector>
#include <map>
#include <cstring>
#include <stdexcept>
#include <sstream>
#include <iostream>
#include <chrono>

// [DEFECT S4] Static nonce counter — resets to 0 on every process restart.
// For any given key, nonce reuse is guaranteed after restart.
static uint64_t g_nonce_counter = 0;

// [DEFECT S1] No authentication key — inter-component messages unauthenticated.
struct Message {
    uint64_t sequence;
    std::string payload;
    // Missing: HMAC or AEAD authentication tag
};

struct Key {
    std::string key_id;
    std::vector<uint8_t> key_material; // [DEFECT S2] Should be a secure buffer
    std::chrono::system_clock::time_point created_at;
    bool consumed = false;
};

class KeyManager {
public:
    // [DEFECT S3] Key material not zeroized on destruction — plain destructor.
    ~KeyManager() {
        // keys_ will be destroyed here, but std::vector<uint8_t> does NOT
        // zeroize its contents before freeing. Key bytes remain in heap memory.
    }

    // Store a new key from the QKD module.
    void store_key(const std::string& key_id, const std::vector<uint8_t>& key) {
        Key k;
        k.key_id = key_id;
        k.key_material = key; // [DEFECT S2] Unnecessary heap copy of key material
        k.created_at = std::chrono::system_clock::now();
        keys_[key_id] = k;

        // [DEFECT S2] Key material logged — CRITICAL violation
        std::ostringstream oss;
        for (auto b : key) {
            oss << std::hex << static_cast<int>(b);
        }
        std::cout << "Stored key " << key_id << ": " << oss.str() << std::endl;
    }

    // Retrieve a key for consumption.
    std::vector<uint8_t> consume_key(const std::string& key_id) {
        auto it = keys_.find(key_id);
        if (it == keys_.end()) {
            throw std::runtime_error("Key not found: " + key_id);
        }

        // [DEFECT S5] Non-atomic key consumption: key is returned but not
        // immediately marked as consumed. Another thread could consume the
        // same key between this read and the line below.
        auto key_copy = it->second.key_material;
        it->second.consumed = true;  // Race condition window here

        // [DEFECT S3] After returning, key_copy goes out of scope without
        // zeroization. The caller receives a copy; neither copy is zeroized.
        return key_copy;
    }

    // Encrypt a message using the next nonce.
    std::vector<uint8_t> encrypt(const std::vector<uint8_t>& plaintext,
                                  const std::vector<uint8_t>& key) {
        // [DEFECT S4] Nonce reuse: g_nonce_counter resets on restart.
        // Any long-running or restarted service will reuse nonces.
        uint64_t nonce = g_nonce_counter++;

        // [DEFECT — custom crypto] Rolling a custom XOR cipher — CRITICAL.
        // Must use an audited AEAD library (libsodium, OpenSSL AES-GCM).
        std::vector<uint8_t> ciphertext(plaintext.size());
        for (size_t i = 0; i < plaintext.size(); i++) {
            ciphertext[i] = plaintext[i] ^ key[i % key.size()] ^ (nonce & 0xFF);
        }
        return ciphertext;
    }

    // Check QBER and decide whether to continue.
    bool check_qber(double qber) {
        // [DEFECT S5] QBER threshold not enforced: returns true (continue) even
        // above the BB84 abort threshold of ~11%.
        if (qber > 0.20) {
            std::cout << "QBER very high: " << qber << std::endl;
            return false;
        }
        // Missing: abort when qber > 0.11 (BB84 threshold)
        return true; // Silent continuation above threshold
    }

    // Process an incoming message from a peer component.
    void process_message(const Message& msg) {
        // [DEFECT S1] No authentication check — message accepted without
        // verifying an HMAC or AEAD tag. Any forged or replayed message is
        // processed as legitimate.
        // [DEFECT S1] No sequence number validation — replay attacks possible.
        handle_payload(msg.payload);
    }

private:
    void handle_payload(const std::string& payload) {
        // Application logic stub
        (void)payload;
    }

    std::map<std::string, Key> keys_;
};

int main() {
    KeyManager km;

    // Example usage (illustrating the defects above)
    std::vector<uint8_t> raw_key = {0x01, 0x02, 0x03, 0x04};
    km.store_key("key-001", raw_key);

    auto key = km.consume_key("key-001");
    // [DEFECT S3] 'key' never zeroized before going out of scope

    Message msg{42, "QKD_SIFT_BASES:..."};
    km.process_message(msg);  // [DEFECT S1] No authentication

    return 0;
}
