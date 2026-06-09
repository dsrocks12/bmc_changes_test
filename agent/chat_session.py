"""
Registry-driven chat session for CLI and HTTP (one message in, assistant reply out).
"""

from __future__ import annotations

from typing import Optional

from intent_router import classify_top_intent, load_intent_registry, match_intent_heuristic
from tool_generator import generate_tools

from agent import (
    REGISTRY_PATH,
    build_api_catalog,
    collect_required_from_message,
    load_registry,
    phase1_detect_intent,
    populate_params_from_query,
    try_finalize_api_call,
    warmup_llm,
)


class AutomationChatSession:
    """One conversation thread backed by api_registry.yaml tools."""

    def __init__(self):
        registry = load_registry()
        self.intent_registry = load_intent_registry()
        self.apis = registry["apis"]
        tools = generate_tools(REGISTRY_PATH)
        self.tool_map = {t.name: t for t in tools}
        self.api_map = {a["id"]: a for a in self.apis}
        self.api_catalog = build_api_catalog(self.apis)

        self.history: list[dict] = []
        self.state = "IDLE"
        self.current_api: Optional[str] = None
        self.raw_params: dict = {}
        self.original_query = ""
        self._replies: list[str] = []

    def reset(self):
        self.state = "IDLE"
        self.current_api = None
        self.raw_params = {}
        self.original_query = ""

    def _say(self, msg: str, *, prefix: str = ""):
        text = f"{prefix}{msg}" if prefix else msg
        self._replies.append(text)
        self.history.append({"role": "assistant", "content": msg})

    def _finalize_or_collect(self, source_text: str):
        api = self.api_map[self.current_api]
        result = try_finalize_api_call(
            api,
            self.raw_params,
            source_text,
            self.tool_map,
            self.original_query,
        )
        if result["status"] == "collect":
            self.state = "COLLECT_REQUIRED"
            self._say(result["message"])
        elif result["status"] == "success":
            self._say(result["message"])
            self.reset()
        else:
            self._say(result["message"])
            self.reset()

    def handle(self, user_input: str) -> str:
        """Process one user message; return combined assistant reply text."""
        self._replies = []
        text = (user_input or "").strip()
        if not text:
            return ""

        low = text.lower()
        if low in ("exit", "quit", "bye"):
            self._say("Goodbye!")
            return "\n\n".join(self._replies)

        self.history.append({"role": "user", "content": text})

        if low in ("start over", "reset", "cancel", "nevermind", "new"):
            self.reset()
            self._say("No problem! What would you like to do?")
            return "\n\n".join(self._replies)

        if self.state != "IDLE":
            top_hit = match_intent_heuristic(text, self.intent_registry)
            if top_hit in ("chitchat", "help"):
                self.reset()
                top = classify_top_intent(
                    text, self.intent_registry, self.apis, self.history
                )
                self._say(top["reply"])
                return "\n\n".join(self._replies)

        if self.state == "IDLE":
            self._handle_idle(text)
        elif self.state == "COLLECT_REQUIRED":
            self._handle_collect_required(text)

        return "\n\n".join(self._replies)

    def _handle_idle(self, user_input: str):
        self.original_query = user_input

        top = classify_top_intent(
            user_input, self.intent_registry, self.apis, self.history
        )
        if top["intent"] == "chitchat":
            self._say(top["reply"])
            return
        if top["intent"] == "help":
            self._say(top["reply"])
            return

        intent = phase1_detect_intent(
            user_input, self.api_catalog, self.history, set(self.api_map)
        )
        api_id = intent.get("api_id")

        if not api_id or api_id not in self.api_map:
            reply = intent.get("reply")
            if reply and str(reply).lower() != "null":
                self._say(reply)
            else:
                reason = intent.get("reason", "Could you be more specific?")
                self._say(
                    f"I'm not sure which API fits that request. {reason}\n\n"
                    "Try describing the automation task (e.g. 'list centralized "
                    "connection profiles of type Database')."
                )
            return

        self.current_api = api_id
        api = self.api_map[api_id]
        self.raw_params = {}
        populate_params_from_query(api, self.original_query, self.raw_params)
        self._finalize_or_collect(self.original_query)

    def _handle_collect_required(self, user_input: str):
        api = self.api_map[self.current_api]
        collect_required_from_message(user_input, api, self.raw_params)
        source_text = f"{self.original_query}\n{user_input}".strip()
        self._finalize_or_collect(source_text)


class SessionStore:
    """In-memory sessions keyed by widget session_id."""

    def __init__(self):
        self._sessions: dict[str, AutomationChatSession] = {}
        self._warmed = False

    def ensure_warmup(self):
        if not self._warmed:
            warmup_llm()
            self._warmed = True

    def get(self, session_id: str) -> AutomationChatSession:
        if session_id not in self._sessions:
            self._sessions[session_id] = AutomationChatSession()
        return self._sessions[session_id]

    def reset(self, session_id: str):
        self._sessions.pop(session_id, None)


store = SessionStore()
