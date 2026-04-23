# AI-agent-PC (Offline Desktop Assistant MVP)

AI-agent-PC is a **local-only desktop assistant MVP** designed to run offline with a Tkinter UI, SQLite persistence, guarded system tools, monitoring alerts, routines, and mock/partial voice support.

## What this MVP is

A stable, usable local app focused on:

- clean startup and shutdown lifecycle
- background monitoring with safe thread handling
- auditable local actions/events
- SQLite-backed persistence (alerts, routines, trusted targets, settings)
- minimal but functional desktop UX for core flows

## Core features

- **Chat assistant panel**
  - text input routed through a local orchestrator
  - structured assistant responses
  - permission-aware handling for safe/medium/high-risk actions
- **System tools (offline placeholders + local reads)**
  - current system status
  - top processes
  - trusted app/folder action placeholders
- **Monitoring + alerts**
  - periodic local checks (CPU/RAM/Disk/process heuristics)
  - alert deduplication window
  - persisted alerts in SQLite
- **Routines**
  - SQLite-backed built-in routines
  - permission checks + trusted-target validation per step
- **Voice (mock/partial)**
  - push-to-talk/start-stop UX
  - mock STT/TTS adapters for local integration testing
  - voice toggles persisted in SQLite settings
- **Audit logging**
  - local app events and action outcomes saved in SQLite
  - application log file at `.data/app.log`

## Installation

### Requirements

- Python 3.11+
- tkinter available in your Python runtime (usually included in standard Python installers)

### Steps

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install in editable mode:

```bash
pip install -e .[dev]
```

## How to run

### Start the desktop app

```bash
ai-agent-pc
```

or

```bash
python -m ai_agent_pc.main
```

### Optional: initialize DB ahead of time

```bash
python scripts/init_db.py
```

### Run tests

```bash
pytest
```

## Runtime behavior

- App bootstraps `.data/agent.db` and schema automatically.
- Monitoring starts in a background daemon thread at app startup.
- Monitoring stops cleanly on app shutdown.
- Voice settings (`stt_enabled`, `tts_enabled`, `push_to_talk`) persist in SQLite.
- Fatal startup/runtime exceptions are logged and surfaced with a clear CLI message.

## Current limitations

- No cloud/online integrations (intentional).
- STT/TTS are mock adapters (architecture ready, engine integration pending).
- Tool actions are intentionally conservative placeholders for MVP safety.
- UI is Tkinter-based and intentionally minimal.

## Packaging notes (basic)

A simple executable build path is feasible with PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile -n ai-agent-pc src/ai_agent_pc/main.py
```

Notes:
- Validate tkinter support in the target OS image.
- Test read/write permissions for the `.data/` directory where SQLite and logs are stored.

## Roadmap (next stability-focused steps)

1. Replace mock STT/TTS with real offline engines (e.g., whisper.cpp + local TTS).
2. Expand settings UI to persist monitoring thresholds and trusted target edits.
3. Add richer error surfacing in UI (non-blocking toast/panel + retry guidance).
4. Add platform packaging scripts and signed distributions per OS.
5. Add more end-to-end integration tests around UI-triggered lifecycle transitions.
