#!/usr/bin/env python3
"""
HTTP API for the BMC chat widget.

POST /api/chat  { "message": "...", "session_id": "..." }
→ { "response": "..." }

All BMC calls go through api_registry.yaml + tool_generator (same as agent CLI).
"""

from __future__ import annotations

import os
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

from chat_session import store

load_dotenv()

app = Flask(__name__)
CORS(
    app,
    resources={r"/api/*": {"origins": os.getenv("CORS_ORIGINS", "*")}},
)

store.ensure_warmup()


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "bmc-automation-agent"})


@app.post("/api/chat")
def api_chat():
    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    session_id = (body.get("session_id") or "").strip() or str(uuid.uuid4())

    if not message:
        return jsonify({"error": "message is required"}), 400

    session = store.get(session_id)
    try:
        response = session.handle(message)
    except Exception as exc:
        app.logger.exception("chat error session=%s", session_id)
        return jsonify(
            {
                "session_id": session_id,
                "response": f"Something went wrong on the agent: {exc}",
            }
        ), 500

    return jsonify({"session_id": session_id, "response": response or ""})


@app.post("/api/chat/reset")
def api_chat_reset():
    body = request.get_json(silent=True) or {}
    session_id = (body.get("session_id") or "").strip()
    if session_id:
        store.reset(session_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    # Default 5001 — macOS often reserves 5000 for AirPlay Receiver
    port = int(os.getenv("AGENT_PORT", "5001"))
    print(f"\nBMC Automation Agent API on http://localhost:{port}/api/chat\n")
    if port == 5000:
        print(
            "Tip: If this port fails, set AGENT_PORT=5001 (AirPlay uses 5000 on macOS).\n"
        )
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
