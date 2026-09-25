//! TLS 1.3 handshake, from both sides, in one process.
//!
//! Runs a real server and a real client (via `rustls`, a production TLS
//! implementation — this demo does not hand-roll any cryptography) connected
//! over a real loopback TCP socket, and prints every step each side takes:
//! the raw record-layer bytes going over the wire, and the milestones inside
//! the handshake state machine (certificate verification, key derivation,
//! Finished messages).
//!
//! Run with `RUST_LOG=debug` or `RUST_LOG=trace` to also see rustls's own
//! internal per-message logging (ClientHello contents, ServerHello contents,
//! key schedule steps, etc.) interleaved with the `[client]`/`[server]`
//! lines below.

mod cert;
mod client;
mod server;

use std::net::TcpListener;

fn main() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info"))
        .format_timestamp(None)
        .init();

    println!("=== step 0: generate a self-signed cert for \"localhost\" (not part of TLS itself) ===\n");
    let localhost_cert = cert::generate();

    println!("=== step 1: server starts listening ===\n");
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind an ephemeral loopback port");
    let addr = listener.local_addr().expect("bound listener has a local addr");
    println!("[server] listening on {addr}\n");

    let server_config = server::build_config(&localhost_cert);

    let server_thread = std::thread::spawn(move || {
        let (sock, _) = listener.accept().expect("accept the client's connection");
        println!("=== step 2: TCP accepted, TLS handshake begins (server side) ===\n");
        server::handle_connection(sock, server_config);
    });

    // Give the server thread a moment to reach `accept()`. In production
    // code you'd synchronize this properly; for a linear demo transcript,
    // a short sleep keeps the printed steps from interleaving oddly.
    std::thread::sleep(std::time::Duration::from_millis(50));

    println!("=== step 2: TLS handshake begins (client side) ===\n");
    let client_config = client::build_config(&localhost_cert.cert_der);
    client::connect_and_echo(addr, client_config, "hello over TLS");

    server_thread.join().expect("server thread should not panic");

    println!("\n=== done: both sides completed the handshake and exchanged encrypted data ===");
}
