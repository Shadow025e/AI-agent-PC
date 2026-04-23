# AI-agent-PC

Local-first, Python-based AI agent scaffold focused on secure orchestration and modular extensibility.

## MVP scaffold scope (this step)

This repository currently includes only foundational structure:

- package/module layout for core layers
- minimal app shell entrypoint
- local SQLite bootstrap
- placeholder interfaces with TODO markers
- basic tests

### Not implemented yet

- full agent planning/execution logic
- online/cloud integrations
- production security policy engine
- native offline audio engine integrations (STT/TTS currently mock adapters)

## Project layout

```text
src/ai_agent_pc/
  app.py                 # app composition shell
  main.py                # CLI entrypoint
  config.py              # base config loader
  ui/
  orchestrator/
  tools/
  security/
  monitoring/
  db/
  routines/
  voice/
scripts/
  init_db.py             # SQLite bootstrap entrypoint
tests/
```


## Offline voice MVP (current)

Implemented in this step:

- offline voice service layer with pluggable STT/TTS adapter interfaces
- mock local recorder + STT + TTS adapters for architecture validation
- chat UI microphone flow (start/stop + hold-to-talk)
- transcription injection into the same orchestrator path used by typed text
- optional assistant response speech toggle (mock TTS)

Deferred (explicit TODO integration points):

- whisper.cpp (or equivalent) binding for real offline STT
- native/local offline TTS engine playback
- platform audio device selection and persistence

## Setup

1. Create a virtual environment and activate it.
2. Install package in editable mode with dev dependencies:

```bash
pip install -e .[dev]
```

## Run scaffold

```bash
ai-agent-pc
```

or:

```bash
python -m ai_agent_pc.main
```

Initialize SQLite explicitly:

```bash
python scripts/init_db.py
```

## Run tests

```bash
pytest
```

## Next implementation priorities

1. Build permission scopes and consent workflows.
2. Implement orchestrator execution loop with guarded tool calls.
3. Add SQLite-backed monitoring/event persistence.
4. Replace mock STT/TTS/recording adapters with native offline engines.
5. Expand settings persistence and richer voice UX controls.
