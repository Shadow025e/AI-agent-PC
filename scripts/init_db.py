"""Manual migration/bootstrap entrypoint for local development."""

from ai_agent_pc.config import load_config
from ai_agent_pc.db.sqlite import initialize_sqlite


if __name__ == "__main__":
    config = load_config()
    initialize_sqlite(config.db_path)
    print(f"Initialized SQLite at {config.db_path}")
