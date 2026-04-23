"""CLI entrypoint for the minimal scaffold."""

import logging
import traceback

from ai_agent_pc.app import create_app


_HEADLESS_DISPLAY_ERROR_SNIPPETS = (
    "no display name and no $display environment variable",
    "couldn't connect to display",
)


def _is_headless_display_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(snippet in message for snippet in _HEADLESS_DISPLAY_ERROR_SNIPPETS)


def main() -> None:
    try:
        app = create_app()
        app.run()
    except Exception as exc:  # pragma: no cover - final crash boundary
        logging.getLogger(__name__).exception("Fatal startup/runtime error: %s", exc)
        if _is_headless_display_error(exc):
            print(
                "Application failed to start: no graphical display is available. "
                "Run in a desktop session or set DISPLAY before launching the Tkinter UI."
            )
            raise SystemExit(1) from exc

        print("Application failed to start or crashed. See .data/app.log for details.")
        print(traceback.format_exc(limit=3))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
