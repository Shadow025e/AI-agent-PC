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
- rich UI and voice feature implementation

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
4. Flesh out routines and voice adapters with local/offline providers.
5. Expand UI from shell placeholder into interactive experience.
