"""Voice input/output adapters placeholders."""


class VoiceAdapter:
    """Abstract voice adapter boundary.

    TODO: Define offline STT/TTS adapter interfaces and local providers.
    """

    def transcribe(self, _: bytes) -> str:
        raise NotImplementedError

    def synthesize(self, _: str) -> bytes:
        raise NotImplementedError
