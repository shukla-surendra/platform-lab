"""
Admission webhook server - stdlib only, no framework, so the AdmissionReview protocol itself
is visible rather than hidden behind a library's decorators.

Two endpoints, both real Kubernetes admission mechanisms:

  /validate  - ValidatingAdmissionWebhook: rejects a Pod create that has no `team` label.
               Can only ever answer allowed: true/false - it cannot change the object.
  /mutate    - MutatingAdmissionWebhook: injects a `webhook-demo/injected: "true"` annotation
               via a JSONPatch, if not already present. Runs BEFORE validation in the real
               admission chain (mutating -> validating), though this demo's two webhooks don't
               depend on each other's output.

kube-apiserver only calls a webhook over HTTPS with a certificate it's been told to trust
(the CA bundle in the WebhookConfiguration) - hence the self-signed cert this server loads.
"""

import base64
import http.server
import json
import ssl

REQUIRED_LABEL = "team"
INJECTED_ANNOTATION = "webhook-demo/injected"


def admission_response(uid, allowed, message=None, patch=None):
    response = {"uid": uid, "allowed": allowed}
    if message:
        response["status"] = {"message": message}
    if patch is not None:
        response["patch"] = base64.b64encode(json.dumps(patch).encode()).decode()
        response["patchType"] = "JSONPatch"
    return {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "response": response,
    }


def handle_validate(admission_request):
    uid = admission_request["uid"]
    obj = admission_request["object"]
    labels = (obj.get("metadata") or {}).get("labels") or {}
    name = obj.get("metadata", {}).get("generateName") or obj.get("metadata", {}).get("name", "<unnamed>")

    if REQUIRED_LABEL not in labels:
        return admission_response(
            uid, allowed=False,
            message=f"pod '{name}' rejected: missing required label '{REQUIRED_LABEL}'",
        )
    return admission_response(uid, allowed=True)


def handle_mutate(admission_request):
    uid = admission_request["uid"]
    obj = admission_request["object"]
    annotations = (obj.get("metadata") or {}).get("annotations")

    if annotations and INJECTED_ANNOTATION in annotations:
        return admission_response(uid, allowed=True)  # already present, no-op patch

    if annotations is None:
        patch = [{
            "op": "add", "path": "/metadata/annotations",
            "value": {INJECTED_ANNOTATION: "true"},
        }]
    else:
        patch = [{
            "op": "add",
            "path": f"/metadata/annotations/{INJECTED_ANNOTATION.replace('/', '~1')}",
            "value": "true",
        }]
    return admission_response(uid, allowed=True, patch=patch)


class Handler(http.server.BaseHTTPRequestHandler):
    def _handle(self, fn):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        review = fn(body["request"])
        payload = json.dumps(review).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if self.path == "/validate":
            self._handle(handle_validate)
        elif self.path == "/mutate":
            self._handle(handle_mutate)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        print(f"[webhook] {self.address_string()} - {fmt % args}")


def main():
    server = http.server.HTTPServer(("0.0.0.0", 8443), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile="/certs/tls.crt", keyfile="/certs/tls.key")
    # Without this, ALPN is left unnegotiated. Go's http.Transport (what kube-apiserver's
    # webhook client uses) offers "h2" by default; against a server that never answers the
    # ALPN extension at all, the handshake can hang rather than cleanly falling back to
    # HTTP/1.1 - confirmed empirically (kube-apiserver's dispatcher logged a generic "could
    # not find the requested resource" for every call, and this stdlib server's own request
    # log stayed completely empty - the request never arrived; forcing http/1.1 here fixed it).
    ctx.set_alpn_protocols(["http/1.1"])
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    print("admission webhook listening on :8443 (TLS)")
    server.serve_forever()


if __name__ == "__main__":
    main()
