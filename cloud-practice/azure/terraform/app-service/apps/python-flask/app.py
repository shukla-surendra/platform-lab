import os
import platform
import socket

from flask import Flask, jsonify

# Oryx (App Service's build system) auto-detects a Flask app named `app`
# in app.py and starts it with gunicorn -- no startup command needed.
app = Flask(__name__)


@app.get("/")
def index():
    return jsonify(
        app="python-flask",
        message=os.environ.get("GREETING", "hello"),
        # Set by the App Service platform itself, not by us:
        site=os.environ.get("WEBSITE_SITE_NAME"),
        slot=os.environ.get("WEBSITE_SLOT_NAME", "production"),
        instance=os.environ.get("WEBSITE_INSTANCE_ID", "local")[:12],
        sku=os.environ.get("WEBSITE_SKU"),
        host=socket.gethostname(),
        python=platform.python_version(),
    )


@app.get("/health")
def health():
    # Target of site_config.health_check_path -- the platform pings this
    # and pulls an instance out of rotation if it keeps failing.
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 8000)))
