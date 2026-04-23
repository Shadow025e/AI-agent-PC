from pathlib import Path

from ai_agent_pc.config import MonitoringConfig
from ai_agent_pc.db.sqlite import AuditLogger
from ai_agent_pc.monitoring.models import ProcessUsage, SystemSnapshot
from ai_agent_pc.monitoring.service import MonitoringService
from ai_agent_pc.orchestrator.agent_orchestrator import AgentOrchestrator
from ai_agent_pc.security.permissions import PermissionManager
from ai_agent_pc.tools.registry import ToolRegistry
from ai_agent_pc.voice.adapters import (
    MockSpeechToTextAdapter,
    MockTextToSpeechAdapter,
    SpeechToTextAdapter,
    TranscriptionResult,
)
from ai_agent_pc.voice.service import RecordingState, VoiceService, VoiceSettings


class StubCollector:
    def snapshot(self):
        return SystemSnapshot(cpu_percent=22, ram_percent=33, disk_percent=44, battery_percent=None, battery_status=None)

    def top_processes(self, limit: int = 5):
        return [ProcessUsage(pid=1, name="proc", cpu_percent=11, ram_percent=1.5)][:limit]

    def startup_entries(self):
        return []

    def recent_crash_count(self, window_seconds: int = 3600):
        return 0


def _make_orchestrator(tmp_path: Path) -> tuple[AgentOrchestrator, MonitoringService, AuditLogger]:
    db_path = tmp_path / "agent.db"
    monitoring = MonitoringService(
        db_path=db_path,
        config=MonitoringConfig(),
        collector=StubCollector(),
    )
    orchestrator = AgentOrchestrator(
        permissions=PermissionManager(),
        tools=ToolRegistry(),
        monitoring=monitoring,
    )
    return orchestrator, monitoring, AuditLogger(db_path)


class FailingSTT(SpeechToTextAdapter):
    def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        return TranscriptionResult(text="", error="transcription failed")


def test_voice_recording_state_transitions() -> None:
    voice = VoiceService()

    start = voice.start_recording()
    assert start.error is None
    assert voice.state is RecordingState.RECORDING

    stop = voice.stop_recording_and_transcribe()
    assert stop.error is None
    assert stop.transcription is not None
    assert voice.state is RecordingState.IDLE


def test_transcription_routes_into_existing_orchestrator_flow(tmp_path: Path) -> None:
    orchestrator, _, _ = _make_orchestrator(tmp_path)
    voice = VoiceService(stt=MockSpeechToTextAdapter())

    voice.start_recording()
    transcript = voice.stop_recording_and_transcribe()
    assert transcript.error is None
    assert transcript.transcription is not None

    response = orchestrator.handle_request(transcript.transcription)
    assert response.status == "ok"


def test_tts_respects_enable_disable_toggle() -> None:
    tts = MockTextToSpeechAdapter()
    voice = VoiceService(tts=tts, settings=VoiceSettings(tts_enabled=False))

    voice.speak_response("hello")
    assert tts.last_spoken is None

    voice.settings.tts_enabled = True
    voice.speak_response("hello")
    assert tts.last_spoken == "hello"


def test_stt_failure_is_exposed_cleanly() -> None:
    voice = VoiceService(stt=FailingSTT())
    voice.start_recording()

    result = voice.stop_recording_and_transcribe()

    assert result.error == "transcription failed"
