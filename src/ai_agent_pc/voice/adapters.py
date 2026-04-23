"""Offline voice adapter interfaces and local placeholder implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class TranscriptionResult:
    """Result returned by an STT adapter."""

    text: str
    error: str | None = None


class SpeechToTextAdapter(ABC):
    """Offline speech-to-text adapter boundary.

    Implementations should remain local-only (no cloud/network calls).
    """

    @abstractmethod
    def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        """Convert recorded audio bytes into text."""


class TextToSpeechAdapter(ABC):
    """Offline text-to-speech adapter boundary."""

    @abstractmethod
    def speak(self, text: str) -> None:
        """Speak text with a local engine (or placeholder)."""


class MockSpeechToTextAdapter(SpeechToTextAdapter):
    """Deterministic local placeholder for MVP wiring.

    TODO: replace with real offline implementation (e.g. whisper.cpp bridge).
    """

    def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        if not audio_bytes:
            return TranscriptionResult(text="", error="No audio captured.")
        token_count = max(1, len(audio_bytes) // 64)
        return TranscriptionResult(text=f"mock transcription ({token_count} frames)")


class MockTextToSpeechAdapter(TextToSpeechAdapter):
    """No-op placeholder that records last spoken text for tests/debugging."""

    def __init__(self) -> None:
        self.last_spoken: str | None = None

    def speak(self, text: str) -> None:
        self.last_spoken = text
