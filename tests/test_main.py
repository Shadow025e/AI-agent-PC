import pytest

from ai_agent_pc import main


class _FakeApp:
    def run(self) -> None:
        return None


class _HeadlessFailingApp:
    def run(self) -> None:
        raise RuntimeError("no display name and no $DISPLAY environment variable")


class _GenericFailingApp:
    def run(self) -> None:
        raise RuntimeError("unexpected startup failure")


def test_main_runs_app(monkeypatch) -> None:
    monkeypatch.setattr(main, "create_app", lambda: _FakeApp())

    main.main()


def test_main_reports_headless_display_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr(main, "create_app", lambda: _HeadlessFailingApp())

    with pytest.raises(SystemExit):
        main.main()

    output = capsys.readouterr().out
    assert "no graphical display is available" in output


def test_main_reports_generic_startup_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr(main, "create_app", lambda: _GenericFailingApp())

    with pytest.raises(SystemExit):
        main.main()

    output = capsys.readouterr().out
    assert "Application failed to start or crashed" in output
