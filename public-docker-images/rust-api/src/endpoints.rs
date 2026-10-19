//! One table describing every route, consumed by two things that must never
//! disagree: `GET /api/endpoints` (the machine-readable reference) and the
//! landing page's endpoint table (the human one). Both are generated from
//! this list rather than maintained by hand in two places — the alternative
//! is exactly the kind of silent drift this codebase has hit before: docs
//! that describe a route which moved, or a route nobody wrote down.
//!
//! Adding a route means adding one entry here. Nothing else needs editing for
//! it to show up in both references.

use std::sync::OnceLock;

use axum::Json;
use serde_json::{Value, json};

pub struct Endpoint {
    pub methods: &'static [&'static str],
    /// The route pattern as registered with the router, e.g. `/api/test/status/{code}`.
    pub path: &'static str,
    /// A concrete, callable instance of `path` — `/api/test/status/503` for
    /// the pattern above. Drives the landing page's live links; irrelevant to
    /// the JSON output, which reports `path` (the real route) either way.
    pub example: Option<&'static str>,
    pub description: &'static str,
    pub group: &'static str,
}

pub const ENDPOINTS: &[Endpoint] = &[
    Endpoint {
        methods: &["GET"],
        path: "/",
        example: None,
        description: "Landing page — every endpoint, with a live example",
        group: "Health & identity",
    },
    Endpoint {
        methods: &["GET"],
        path: "/version",
        example: None,
        description: "Which binary is actually answering: name, version, os, arch",
        group: "Health & identity",
    },
    Endpoint {
        methods: &["GET"],
        path: "/healthz",
        example: None,
        description: "Liveness — is the process answering HTTP at all",
        group: "Health & identity",
    },
    Endpoint {
        methods: &["GET"],
        path: "/readyz",
        example: None,
        description: "Readiness. Identical to /healthz — nothing downstream to be unready for",
        group: "Health & identity",
    },
    Endpoint {
        methods: &["GET"],
        path: "/api/endpoints",
        example: None,
        description: "This table, as JSON — the machine-readable form of this page",
        group: "Health & identity",
    },
    Endpoint {
        methods: &["POST"],
        path: "/debug/logstorm",
        example: Some("/debug/logstorm?count=500&tag=x"),
        description: "Emits an exact, known number of lines at known levels; reports emitted vs suppressed by RUST_LOG — a reference count for proving a log pipeline loses nothing",
        group: "Log generation",
    },
    Endpoint {
        methods: &["POST"],
        path: "/debug/random-logs",
        example: Some("/debug/random-logs?count=200"),
        description: "Emits a random volume of realistic, randomly-worded log lines at a realistic level mix — for testing dashboards and parsers against traffic that looks like production",
        group: "Log generation",
    },
    Endpoint {
        methods: &["GET", "POST", "PUT"],
        path: "/api/test/echo",
        example: Some("/api/test/echo?hello=world"),
        description: "Echoes method, path, query, headers, body — parsed as JSON when it is JSON",
        group: "API testing",
    },
    Endpoint {
        methods: &["GET"],
        path: "/api/test/status/{code}",
        example: Some("/api/test/status/503"),
        description: "Returns that status code, with its canonical reason phrase",
        group: "API testing",
    },
    Endpoint {
        methods: &["GET"],
        path: "/api/test/delay/{ms}",
        example: Some("/api/test/delay/1500"),
        description: "Sleeps, then responds. Capped at 30s",
        group: "API testing",
    },
    Endpoint {
        methods: &["GET"],
        path: "/api/test/uuid",
        example: None,
        description: "A v4 UUID",
        group: "API testing",
    },
    Endpoint {
        methods: &["GET"],
        path: "/api/test/headers",
        example: None,
        description: "Request headers as this server received them",
        group: "API testing",
    },
    Endpoint {
        methods: &["GET"],
        path: "/api/test/ip",
        example: None,
        description: "Peer address + forwarding headers. Behind a proxy, the peer IS the proxy",
        group: "API testing",
    },
    Endpoint {
        methods: &["GET"],
        path: "/api/test/bytes/{n}",
        example: Some("/api/test/bytes/2048"),
        description: "Deterministic payload of n bytes. Capped at 10 MB",
        group: "API testing",
    },
    Endpoint {
        methods: &["GET"],
        path: "/api/test/json",
        example: Some("/api/test/json?count=3"),
        description: "A fixed-shape JSON document for deserialisation tests",
        group: "API testing",
    },
];

pub async fn list() -> Json<Value> {
    let endpoints: Vec<Value> = ENDPOINTS
        .iter()
        .map(|e| {
            json!({
                "methods": e.methods,
                "path": e.path,
                "description": e.description,
                "group": e.group,
            })
        })
        .collect();
    Json(json!({ "count": endpoints.len(), "endpoints": endpoints }))
}

/// Renders the same table as grouped HTML for the landing page. Cached after
/// the first call — the content is `const`, so recomputing it per request
/// would be pure waste.
pub fn html_rows() -> &'static str {
    static RENDERED: OnceLock<String> = OnceLock::new();
    RENDERED.get_or_init(|| {
        let mut out = String::new();
        let mut current_group = "";
        for e in ENDPOINTS {
            if e.group != current_group {
                out.push_str(&format!("<h2>{}</h2>\n", escape(e.group)));
                current_group = e.group;
            }

            let verbs: String = e
                .methods
                .iter()
                .map(|m| format!(r#"<span class="verb {}">{}</span>"#, m.to_lowercase(), m))
                .collect();

            // A link needs somewhere concrete to point: GET is the method a
            // browser click actually performs, and a bare template pattern
            // like /api/test/status/{code} is not a URL. `example` supplies
            // the concrete instance to link to while still displaying the
            // canonical pattern as the label — matching how a caller should
            // read the route, not just where this one demo happens to point.
            let can_link = e.methods.contains(&"GET");
            let path_html = if let Some(example) = e.example {
                if can_link {
                    format!(
                        r#"<a class="path" href="{}">{}</a>"#,
                        escape(example),
                        escape(e.path)
                    )
                } else {
                    format!(r#"<span class="path">{}</span>"#, escape(example))
                }
            } else if can_link && !e.path.contains('{') {
                format!(
                    r#"<a class="path" href="{}">{}</a>"#,
                    escape(e.path),
                    escape(e.path)
                )
            } else {
                format!(r#"<span class="path">{}</span>"#, escape(e.path))
            };

            out.push_str(&format!(
                "<div class=\"row\">{}{}\n    <span class=\"desc\">{}</span></div>\n",
                verbs,
                path_html,
                escape(e.description),
            ));
        }
        out
    })
}

fn escape(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
}
