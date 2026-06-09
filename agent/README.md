# BMC Automation Agent — LangChain + TinyLlama

A conversational AI agent for BMC Control-M automation APIs. Tools are auto-generated from `api_registry.yaml` and invoked through a local TinyLlama model.

---

## Project structure

```
agent/
├── api_registry.yaml     ← BMC API definitions (endpoints, params, auth)
├── intent_registry.yaml  ← Top-level routing: chitchat / help / tool_call
├── intent_router.py      ← Runs before API selection
├── tool_generator.py     ← YAML → LangChain tools
├── agent.py              ← Main agent (terminal CLI)
├── server.py             ← HTTP API for the UI chat widget
├── llm_provider.py       ← TinyLlama via Hugging Face
├── requirements.txt
└── .env.example          ← AUTOMATION_USER / AUTOMATION_PASS
```

---

## Setup (recommended — any OS)

From the **repo root**:

```bash
npm run install:agent
npm run start:agent
```

Edit `agent/.env` before starting (copy from `.env.example` if needed).

---

## Setup (manual)

**Windows (PowerShell or cmd):**

```bat
cd agent
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python server.py
```

**macOS / Linux:**

```bash
cd agent
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python server.py
```

CLI instead of HTTP: replace `server.py` with `agent.py`.

On first run, Hugging Face downloads `TinyLlama/TinyLlama-1.1B-Chat-v1.0` (~2.2 GB).

List generated tools without chat:

```bash
# after install:agent
# Windows:  agent\.venv\Scripts\python benchmark.py --tools-only
# macOS:    agent/.venv/bin/python benchmark.py --tools-only
```

---

## Adding an API

Add an entry under `apis:` in `api_registry.yaml` — a new tool is generated automatically on restart.

---

## Tech stack

| Component | Technology |
|-----------|------------|
| LLM | TinyLlama 1.1B Chat (local) |
| Agent | 4-phase state machine in `agent.py` / `chat_session.py` |
| Tools | Auto-generated from YAML |
| HTTP | Python `requests` + registry auth |
| Config | YAML + `.env` |
