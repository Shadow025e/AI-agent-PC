"""Voice flow services for offline MVP integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from ai_agent_pc.voice.adapters import (
    MockSpeechToTextAdapter,
    MockTextToSpeechAdapter,
    SpeechToTextAdapter,
    TextToSpeechAdapter,
    TranscriptionResult,
)


class RecordingState(str, Enum):
    IDLE = "idle"
    RECORDING = "recording"


@dataclass(slots=True)
class VoiceSettings:
    stt_enabled: bool = True
    tts_enabled: bool = False
    input_device: str = "Default input device (placeholder)"
    output_voice: str = "Default offline voice (placeholder)"
    push_to_talk: bool = True


class AudioRecorder(Protocol):
    def start(self) -> None: ...
    def stop(self) -> bytes: ...


class MockAudioRecorder:
    """Local recorder placeholder.

    TODO: swap with platform-native microphone capture while keeping this interface.
    """

    def __init__(self) -> None:
        self._is_recording = False

    def start(self) -> None:
        self._is_recording = True

    def stop(self) -> bytes:
        if not self._is_recording:
            return b""
        self._is_recording = False
        return b"offline-audio-placeholder"


@dataclass(slots=True)
class VoiceCaptureResult:
    transcription: str | None = None
    error: str | None = None


class VoiceService:
    """Coordinates recorder + STT + optional TTS for offline flows."""

    def __init__(
        self,
        stt: SpeechToTextAdapter | None = None,
        tts: TextToSpeechAdapter | None = None,
        recorder: AudioRecorder | None = None,
        settings: VoiceSettings | None = None,
    ) -> None:
        self.stt = stt or MockSpeechToTextAdapter()
        self.tts = tts or MockTextToSpeechAdapter()
        self.recorder = recorder or MockAudioRecorder()
        self.settings = settings or VoiceSettings()
        self.state = RecordingState.IDLE

    def start_recording(self) -> VoiceCaptureResult:
        if not self.settings.stt_enabled:
            return VoiceCaptureResult(error="Speech-to-text is disabled in settings.")
        if self.state is RecordingState.RECORDING:
            return VoiceCaptureResult(error="Recording is already in progress.")
        self.recorder.start()
        self.state = RecordingState.RECORDING
        return VoiceCaptureResult()

    def stop_recording_and_transcribe(self) -> VoiceCaptureResult:
        if self.state is not RecordingState.RECORDING:
            return VoiceCaptureResult(error="Recording is not active.")

        self.state = RecordingState.IDLE
        audio = self.recorder.stop()
        result: TranscriptionResult = self.stt.transcribe(audio)
        if result.error:
            return VoiceCaptureResult(error=result.error)
        return VoiceCaptureResult(transcription=result.text)

    def speak_response(self, text: str) -> None:
        if self.settings.tts_enabled and text.strip():
            self.tts.speak(text)
