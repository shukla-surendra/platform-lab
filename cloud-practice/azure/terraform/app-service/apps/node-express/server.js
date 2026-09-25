const express = require("express");
const os = require("os");

const app = express();

// App Service tells the container which port to listen on via PORT.
// Hardcoding a port is the #1 reason a Node app "starts" but never
// answers requests (the platform's warmup probe times out).
const port = process.env.PORT || 3000;

app.get("/", (req, res) => {
  res.json({
    app: "node-express",
    message: process.env.GREETING || "hello",
    site: process.env.WEBSITE_SITE_NAME,
    slot: process.env.WEBSITE_SLOT_NAME || "production",
    instance: (process.env.WEBSITE_INSTANCE_ID || "local").slice(0, 12),
    sku: process.env.WEBSITE_SKU,
    host: os.hostname(),
    node: process.version,
    // App Service terminates TLS at its front end and forwards plain
    // HTTP; the original scheme arrives in this header.
    forwardedProto: req.get("x-forwarded-proto"),
  });
});

app.get("/health", (req, res) => res.json({ status: "ok" }));

app.listen(port, () => console.log(`listening on ${port}`));
