// ── ws_client.cpp ─────────────────────────────────────────────────────────────
// Example WebSocket client with deliberate defects for review practice.
// This is NOT production-quality code — it is an input for the
// cpp-production-engineer skill review workflow.
// ─────────────────────────────────────────────────────────────────────────────

#include <websocketpp/config/asio_client.hpp>
#include <websocketpp/client.hpp>
#include <boost/asio/ssl.hpp>
#include <iostream>
#include <string>
#include <thread>
#include <atomic>

using WsClient = websocketpp::client<websocketpp::config::asio_tls_client>;
using MessagePtr = websocketpp::config::asio_tls_client::message_type::ptr;
using ConnectionHdl = websocketpp::connection_hdl;

// [DEFECT D1] Global mutable state with no mutex protection.
std::string g_last_message;
bool g_connected = false;

// [DEFECT D2] Singleton without mutex-protected mutable operations.
class LogManager {
public:
    static LogManager& instance() {
        static LogManager inst;
        return inst;
    }

    // [DEFECT D3] No severity level; logs everything unconditionally.
    void log(const std::string& msg) {
        // [DEFECT D4] Writes directly to std::cout — not syslog-compatible.
        std::cout << msg << std::endl;
    }

    // [DEFECT D5] No private constructor — singleton can be copy-constructed.
    int level = 0;
};

class WebSocketClient {
public:
    WebSocketClient(const std::string& uri) : uri_(uri) {}

    void connect() {
        // [DEFECT D6] TLS context created with verify_none — security-critical.
        auto tls_ctx = std::make_shared<boost::asio::ssl::context>(
            boost::asio::ssl::context::tlsv12_client);
        tls_ctx->set_verify_mode(boost::asio::ssl::verify_none); // NEVER in production

        client_.set_tls_init_handler([tls_ctx](ConnectionHdl) {
            return tls_ctx;
        });

        client_.set_message_handler([this](ConnectionHdl, MessagePtr msg) {
            on_message(msg->get_payload());
        });

        client_.set_close_handler([this](ConnectionHdl) {
            g_connected = false; // [DEFECT D7] Unprotected write to global
            LogManager::instance().log("Connection closed");
            // [DEFECT D8] No reconnect logic on close
        });

        websocketpp::lib::error_code ec;
        auto con = client_.get_connection(uri_, ec);
        client_.connect(con);

        // [DEFECT D9] Thread is never joined or tracked for lifecycle management
        std::thread([this]() { client_.run(); }).detach();

        g_connected = true; // [DEFECT D10] Race: set before run() completes
    }

    void send(const std::string& payload) {
        // [DEFECT D11] No connection state check before send
        // [DEFECT D12] No mutex protecting hdl_
        websocketpp::lib::error_code ec;
        client_.send(hdl_, payload, websocketpp::frame::opcode::text, ec);
        if (ec) {
            // [DEFECT D13] Key material could be in payload — logging it is CRITICAL
            LogManager::instance().log("Send error for payload: " + payload);
        }
    }

private:
    void on_message(const std::string& payload) {
        // [DEFECT D14] Unprotected write to global shared state
        g_last_message = payload;
        // [DEFECT D15] No per-connection receive buffer for partial records
        process(payload);
    }

    void process(const std::string& data) {
        // Stub: application logic would go here
        (void)data;
    }

    WsClient client_;
    ConnectionHdl hdl_;
    std::string uri_;
};

int main() {
    // [DEFECT D16] Raw new — ownership not transferred to a smart pointer
    WebSocketClient* client = new WebSocketClient("wss://example.com/api");
    client->connect();

    std::this_thread::sleep_for(std::chrono::seconds(5));
    client->send("hello");

    // [DEFECT D17] Memory leak — client never deleted
    return 0;
}
