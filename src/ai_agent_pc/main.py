"""CLI entrypoint for the minimal scaffold."""

import logging
import traceback

from ai_agent_pc.app import create_app


def main() -> None:
    try:
        app = create_app()
        app.run()
    except Exception as exc:  # pragma: no cover - final crash boundary
        logging.getLogger(__name__).exception("Fatal startup/runtime error: %s", exc)
        print("Application failed to start or crashed. See .data/app.log for details.")
        print(traceback.format_exc(limit=3))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
