/**
 * websocket_handler.cpp
 *
 * Mock concurrent WebSocket handler for a QKD ground-station node.
 * Handles multiple simultaneous client sessions that exchange quantum key
 * material over authenticated WebSocket connections.
 *
 * THIS FILE IS AN INTENTIONAL DEFECT SHOWCASE for the cpp-realtime-reviewer
 * skill. It contains real-world classes of bugs typical in concurrent C++
 * systems. Do NOT use this code in production.
 */

#include <algorithm>
#include <atomic>
#include <condition_variable>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <functional>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <openssl/evp.h>
#include <sstream>
#include <string>
#include <thread>
#include <unistd.h>
#include <vector>

// ---------------------------------------------------------------------------
// Session state
// ---------------------------------------------------------------------------

enum class QkdState { HANDSHAKE, KEY_EXCHANGE, AUTHENTICATED, ERROR };

struct Session {
    int      socket_fd;
    QkdState state;
    uint8_t  session_key[32];   // 256-bit symmetric key
    uint64_t bytes_sent;
    uint64_t bytes_received;
    std::string peer_id;
};

// ---------------------------------------------------------------------------
// Global session registry — shared across all handler threads
// ---------------------------------------------------------------------------

std::map<int, Session*> g_sessions;   // fd -> session (raw pointer, no ownership)
std::mutex              g_sessions_mtx;

// ---------------------------------------------------------------------------
// Global statistics — updated from every handler thread
// ---------------------------------------------------------------------------

uint64_t g_total_bytes_in  = 0;   // BUG D1/D2: plain non-atomic, no lock
uint64_t g_total_bytes_out = 0;

// ---------------------------------------------------------------------------
// Shutdown flag
// ---------------------------------------------------------------------------

volatile bool g_shutdown = false;   // BUG D2: volatile, not std::atomic<bool>

// ---------------------------------------------------------------------------
// Logging — naive, NOT thread-safe
// ---------------------------------------------------------------------------

// BUG D5: global non-atomic log level; cout calls unsynchronised
int g_log_level = 2;  // 0=off 1=error 2=info 3=debug

void log_message(int level, const std::string& msg) {
    if (level <= g_log_level) {
        // BUG D5.1: std::cout is not synchronised; output interleaves across threads
        std::cout << "[" << level << "] " << msg << std::endl;  // BUG D4: flushing on hot path
    }
}

// ---------------------------------------------------------------------------
// Key-material helpers
// ---------------------------------------------------------------------------

// BUG D3: raw new/delete for key buffer; no RAII
uint8_t* allocate_key_buffer(size_t len) {
    return new uint8_t[len];
}

void free_key_buffer(uint8_t* buf) {
    // BUG D3: not zeroing before free — key bytes remain in freed memory
    delete[] buf;
}

// ---------------------------------------------------------------------------
// QRNG seed (shared across threads — represents an entropy pool)
// ---------------------------------------------------------------------------

uint32_t g_qrng_seed = 0;           // BUG D1: shared, no synchronisation

void refresh_qrng_seed(uint32_t new_seed) {
    // BUG D1: non-atomic write to a variable read from multiple threads
    g_qrng_seed = new_seed;
}

uint32_t get_qrng_entropy() {
    // BUG D1: non-atomic read
    return g_qrng_seed ^ 0xDEADBEEF;
}

// ---------------------------------------------------------------------------
// WebSocket frame parser — called in the hot receive path
// ---------------------------------------------------------------------------

struct WsFrame {
    bool     fin;
    uint8_t  opcode;
    uint64_t payload_len;
    uint8_t* payload;   // BUG D3: raw owning pointer, no RAII
};

WsFrame* parse_frame(const uint8_t* buf, size_t buf_len) {
    WsFrame* frame = new WsFrame{};  // BUG D3: raw new, exception unsafe

    if (buf_len < 2) {
        delete frame;
        return nullptr;
    }

    frame->fin     = (buf[0] & 0x80) != 0;
    frame->opcode  = buf[0] & 0x0F;
    uint64_t plen  = buf[1] & 0x7F;

    if (plen == 126) {
        if (buf_len < 4) { delete frame; return nullptr; }
        plen = (static_cast<uint64_t>(buf[2]) << 8) | buf[3];
    } else if (plen == 127) {
        if (buf_len < 10) { delete frame; return nullptr; }
        plen = 0;
        for (int i = 0; i < 8; ++i)
            plen = (plen << 8) | buf[2 + i];
    }

    frame->payload_len = plen;
    frame->payload = allocate_key_buffer(plen);  // BUG D3: raw owning pointer

    const size_t header_len = (plen < 126) ? 2 : (plen < 65536) ? 4 : 10;
    if (buf_len < header_len + plen) {
        free_key_buffer(frame->payload);
        delete frame;
        return nullptr;
    }
    std::memcpy(frame->payload, buf + header_len, plen);
    return frame;
}

// ---------------------------------------------------------------------------
// Session management
// ---------------------------------------------------------------------------

void register_session(Session* s) {
    std::lock_guard<std::mutex> lk(g_sessions_mtx);
    g_sessions[s->socket_fd] = s;   // raw pointer stored, ownership unclear
}

void remove_session(int fd) {
    std::lock_guard<std::mutex> lk(g_sessions_mtx);
    auto it = g_sessions.find(fd);
    if (it != g_sessions.end()) {
        // BUG D3: session_key not zeroed before the session is freed
        delete it->second;          // raw delete
        g_sessions.erase(it);
    }
}

// ---------------------------------------------------------------------------
// Key derivation — called during KEY_EXCHANGE state
// ---------------------------------------------------------------------------

bool derive_session_key(Session* s, const uint8_t* ikm, size_t ikm_len) {
    EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_HKDF, nullptr);
    if (!ctx) return false;

    // BUG D3: EVP_PKEY_CTX_free not called on every error path below
    if (EVP_PKEY_derive_init(ctx) <= 0)        return false;  // leaks ctx
    if (EVP_PKEY_CTX_set_hkdf_md(ctx, EVP_sha256()) <= 0) return false;  // leaks ctx

    uint8_t* salt = allocate_key_buffer(16);
    uint32_t entropy = get_qrng_entropy();
    std::memcpy(salt, &entropy, sizeof(entropy));  // only 4 bytes of entropy in 16-byte salt

    if (EVP_PKEY_CTX_set1_hkdf_salt(ctx, salt, 16) <= 0) {
        free_key_buffer(salt);
        return false;  // leaks ctx
    }
    free_key_buffer(salt);

    if (EVP_PKEY_CTX_set1_hkdf_key(ctx, ikm, static_cast<int>(ikm_len)) <= 0) {
        EVP_PKEY_CTX_free(ctx);
        return false;
    }

    size_t key_len = 32;
    if (EVP_PKEY_derive(ctx, s->session_key, &key_len) <= 0) {
        EVP_PKEY_CTX_free(ctx);
        return false;
    }

    EVP_PKEY_CTX_free(ctx);

    // BUG D5: logs the derived key in hex — key material in the log
    std::ostringstream oss;
    oss << "derive_session_key: peer=" << s->peer_id << " key=";
    for (int i = 0; i < 32; ++i)
        oss << std::hex << static_cast<int>(s->session_key[i]);
    log_message(3, oss.str());

    return true;
}

// ---------------------------------------------------------------------------
// Message dispatcher — handles an authenticated session frame
// ---------------------------------------------------------------------------

std::mutex g_dispatch_mtx;

void dispatch_message(Session* s, const uint8_t* payload, size_t len) {
    // BUG D4: mutex acquired before a potentially slow log + processing block
    std::lock_guard<std::mutex> lk(g_dispatch_mtx);

    log_message(3, "dispatch: peer=" + s->peer_id);  // BUG D4: log under lock

    // BUG D4: dynamic allocation inside the dispatch hot path
    std::vector<uint8_t> copy(payload, payload + len);

    // simulate QKD key confirmation round-trip (blocking sleep in hot path)
    // BUG D4: blocking call inside packet handler
    usleep(500);

    g_total_bytes_in += len;   // BUG D1/D2: unsynchronised write to shared counter
}

// ---------------------------------------------------------------------------
// Per-connection handler — runs in its own thread
// ---------------------------------------------------------------------------

void connection_handler(int fd) {
    // BUG D3: raw new for Session, ownership transferred to g_sessions but never
    //         clearly documented; freed in remove_session
    Session* s = new Session{};
    s->socket_fd     = fd;
    s->state         = QkdState::HANDSHAKE;
    s->bytes_sent    = 0;
    s->bytes_received = 0;
    std::memset(s->session_key, 0, 32);

    register_session(s);

    uint8_t buf[4096];
    // BUG D2: g_shutdown is volatile bool, not std::atomic<bool>;
    //         the compiler may cache the value in a register
    while (!g_shutdown) {
        ssize_t n = read(fd, buf, sizeof(buf));  // BUG D4: blocking read on real-time thread
        if (n <= 0) break;

        s->bytes_received += n;
        // BUG D1: unsynchronised access to g_total_bytes_in (also in dispatch_message)
        g_total_bytes_in += static_cast<uint64_t>(n);

        WsFrame* frame = parse_frame(buf, static_cast<size_t>(n));
        if (!frame) {
            log_message(1, "parse error on fd=" + std::to_string(fd));
            continue;
        }

        if (s->state == QkdState::HANDSHAKE) {
            s->peer_id = std::string(reinterpret_cast<char*>(frame->payload),
                                     frame->payload_len);
            s->state = QkdState::KEY_EXCHANGE;
            log_message(2, "handshake complete: peer=" + s->peer_id);

        } else if (s->state == QkdState::KEY_EXCHANGE) {
            if (!derive_session_key(s, frame->payload, frame->payload_len)) {
                s->state = QkdState::ERROR;
                // BUG D5: error message includes raw input data (potential injection)
                log_message(1, "key derivation failed for peer=" + s->peer_id +
                               " input=" + std::string(reinterpret_cast<char*>(frame->payload),
                                                       frame->payload_len));
            } else {
                s->state = QkdState::AUTHENTICATED;
            }

        } else if (s->state == QkdState::AUTHENTICATED) {
            dispatch_message(s, frame->payload, frame->payload_len);
        }

        // BUG D3: frame->payload freed but frame itself is not; memory leak
        free_key_buffer(frame->payload);
        // missing: delete frame;
    }

    remove_session(fd);
    close(fd);
}

// ---------------------------------------------------------------------------
// Broadcast — sends a frame to all connected sessions
// ---------------------------------------------------------------------------

void broadcast_key_refresh(const uint8_t* new_key, size_t key_len) {
    // BUG D1: iterates g_sessions without holding g_sessions_mtx
    for (auto& [fd, session] : g_sessions) {
        if (session->state == QkdState::AUTHENTICATED) {
            ssize_t written = write(fd, new_key, key_len);
            if (written < 0) {
                log_message(1, "broadcast write failed fd=" + std::to_string(fd));
            }
            // BUG D1: unsynchronised write to bytes_sent (may race with connection_handler)
            session->bytes_sent += static_cast<uint64_t>(written);
            // BUG D5: logs key material length + fd, making correlation of key
            //         refresh events with individual sessions trivial
            log_message(3, "key refresh sent to fd=" + std::to_string(fd) +
                           " key_len=" + std::to_string(key_len));
        }
    }
    // BUG D1: unsynchronised write to g_total_bytes_out
    g_total_bytes_out += key_len * g_sessions.size();
}

// ---------------------------------------------------------------------------
// Acceptor loop
// ---------------------------------------------------------------------------

void acceptor_loop(int listen_fd) {
    while (!g_shutdown) {   // BUG D2: volatile, not atomic
        int client_fd = accept(listen_fd, nullptr, nullptr);
        if (client_fd < 0) {
            if (g_shutdown) break;
            log_message(1, "accept() failed");
            continue;
        }
        // BUG D4: std::thread created per connection — unbounded thread count,
        //         dynamic allocation per connection on a real-time node
        std::thread t(connection_handler, client_fd);
        t.detach();  // BUG D3: detached thread; lifecycle not managed
    }
}

// ---------------------------------------------------------------------------
// Statistics reporter — runs in a background thread
// ---------------------------------------------------------------------------

std::mutex              g_stats_cv_mtx;
std::condition_variable g_stats_cv;
bool                    g_stats_ready = false;

void stats_reporter() {
    std::unique_lock<std::mutex> lk(g_stats_cv_mtx);
    // BUG D2: no predicate guard — spurious wake-up will cause premature reporting
    g_stats_cv.wait(lk);

    // BUG D1: reads g_total_bytes_in / g_total_bytes_out without any lock or atomic
    printf("bytes_in=%llu bytes_out=%llu sessions=%zu\n",
           (unsigned long long)g_total_bytes_in,
           (unsigned long long)g_total_bytes_out,
           g_sessions.size());  // BUG D1: g_sessions.size() without lock
}

// ---------------------------------------------------------------------------
// Shutdown — called from a signal handler
// ---------------------------------------------------------------------------

void handle_shutdown_signal(int /*signum*/) {
    // BUG D5/D2: printf is not async-signal-safe; g_shutdown is not atomic
    printf("Shutting down...\n");
    g_shutdown = true;
    g_stats_cv.notify_all();   // BUG: notify_all from signal handler; cv is not signal-safe
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

int main() {
    int listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    // (bind/listen omitted for brevity)

    // BUG D4: acceptor and reporter share the main thread implicitly;
    //         no thread priority or affinity set
    std::thread stats_thread(stats_reporter);
    stats_thread.detach();   // BUG D3: detached, lifecycle unmanaged

    acceptor_loop(listen_fd);

    close(listen_fd);
    return 0;
}
