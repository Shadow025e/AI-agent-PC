from ai_agent_pc.app import create_app


def test_create_app_initializes_components() -> None:
    app = create_app()

    assert app.orchestrator is not None
    assert "get_system_status" in app.tools.list_tools()
