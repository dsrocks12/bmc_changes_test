// ============================================================
//  BMC Control-M — UI Server
//  Run: node index.js
//  Then open: http://localhost:3000
// ============================================================

const express = require("express");
const path = require("path");
const { requestLogger, notFound, errorHandler } = require("./src/middleware");

const app = express();
const publicDir = path.join(__dirname, "public");
const AGENT_BACKEND = process.env.AGENT_URL || "http://127.0.0.1:5001";

app.use(express.json());
app.use(requestLogger);

app.get("/health", (_req, res) => {
  res.json({ ok: true, service: "bmc-control-m-ui", agent: AGENT_BACKEND });
});

// Proxy chat to Python agent (avoids CORS; works on Windows/macOS/Linux)
app.post("/api/chat", async (req, res) => {
  try {
    const upstream = await fetch(`${AGENT_BACKEND}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(req.body),
    });
    const data = await upstream.json();
    res.status(upstream.status).json(data);
  } catch (err) {
    res.status(502).json({
      session_id: req.body?.session_id,
      response:
        "Could not reach the automation agent. In another terminal run: npm run start:agent",
      error: err.message,
    });
  }
});

app.use(express.static(publicDir));

app.use(notFound);
app.use(errorHandler);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`\nBMC Control-M UI running on http://localhost:${PORT}`);
  console.log(`Chat proxy → ${AGENT_BACKEND}/api/chat`);
  console.log("Keep this terminal open. Press Ctrl+C to stop.\n");
});
