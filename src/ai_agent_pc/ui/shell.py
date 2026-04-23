"""Desktop UI shell for the local MVP (offline-only)."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk

from ai_agent_pc.db.sqlite import AuditLogger
from ai_agent_pc.monitoring.service import MonitoringService
from ai_agent_pc.orchestrator.agent_orchestrator import AgentOrchestrator, AgentResponse
from ai_agent_pc.voice.service import RecordingState, VoiceService


class UIShell:
    """Minimal desktop UI with chat + status + alerts + history + settings."""

    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        monitoring: MonitoringService,
        audit_logger: AuditLogger,
        voice: VoiceService,
    ) -> None:
        self.orchestrator = orchestrator
        self.monitoring = monitoring
        self.audit_logger = audit_logger
        self.voice = voice
        self.root: tk.Tk | None = None

        self.chat_output: tk.Text | None = None
        self.chat_input: tk.Entry | None = None
        self.status_text: tk.Text | None = None
        self.alerts_text: tk.Text | None = None
        self.history_text: tk.Text | None = None
        self.offline_var: tk.StringVar | None = None

        self.recording_state_var: tk.StringVar | None = None
        self.transcription_var: tk.StringVar | None = None
        self.stt_enabled_var: tk.BooleanVar | None = None
        self.tts_enabled_var: tk.BooleanVar | None = None
        self.push_to_talk_var: tk.BooleanVar | None = None

    def render_welcome(self) -> None:
        self.root = tk.Tk()
        self.root.title("AI Agent PC - Offline MVP")
        self.root.geometry("1080x720")

        self.offline_var = tk.StringVar(value="● Offline Mode")
        self.recording_state_var = tk.StringVar(value="Mic: idle")
        self.transcription_var = tk.StringVar(value="Last transcription: (none)")

        header = ttk.Frame(self.root)
        header.pack(fill=tk.X, padx=12, pady=8)
        ttk.Label(header, text="AI Agent PC", font=("Arial", 16, "bold")).pack(side=tk.LEFT)
        ttk.Label(header, textvariable=self.offline_var, foreground="green").pack(side=tk.RIGHT)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        chat_tab = ttk.Frame(notebook)
        status_tab = ttk.Frame(notebook)
        alerts_tab = ttk.Frame(notebook)
        history_tab = ttk.Frame(notebook)
        settings_tab = ttk.Frame(notebook)

        notebook.add(chat_tab, text="Chat")
        notebook.add(status_tab, text="System Status")
        notebook.add(alerts_tab, text="Alerts")
        notebook.add(history_tab, text="Action History")
        notebook.add(settings_tab, text="Settings")

        self._build_chat_panel(chat_tab)
        self._build_status_panel(status_tab)
        self._build_alerts_panel(alerts_tab)
        self._build_history_panel(history_tab)
        self._build_settings_panel(settings_tab)

        self.refresh_all()
        self.root.mainloop()

    def _build_chat_panel(self, parent: ttk.Frame) -> None:
        self.chat_output = tk.Text(parent, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_output.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 6))

        voice_row = ttk.Frame(parent)
        voice_row.pack(fill=tk.X, padx=8, pady=(0, 6))
        mic_btn = ttk.Button(voice_row, text="Hold to Talk")
        mic_btn.pack(side=tk.LEFT)
        mic_btn.bind("<ButtonPress-1>", lambda _e: self._start_recording())
        mic_btn.bind("<ButtonRelease-1>", lambda _e: self._stop_recording())
        ttk.Button(voice_row, text="Start", command=self._start_recording).pack(side=tk.LEFT, padx=4)
        ttk.Button(voice_row, text="Stop", command=self._stop_recording).pack(side=tk.LEFT)
        ttk.Label(voice_row, textvariable=self.recording_state_var).pack(side=tk.LEFT, padx=10)

        ttk.Label(parent, textvariable=self.transcription_var, foreground="gray").pack(fill=tk.X, padx=8, pady=(0, 6))

        composer = ttk.Frame(parent)
        composer.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.chat_input = ttk.Entry(composer)
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.chat_input.bind("<Return>", lambda _e: self._send_chat())

        ttk.Button(composer, text="Send", command=self._send_chat).pack(side=tk.LEFT, padx=6)

    def _build_status_panel(self, parent: ttk.Frame) -> None:
        controls = ttk.Frame(parent)
        controls.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(controls, text="Refresh", command=self.refresh_status).pack(side=tk.LEFT)

        self.status_text = tk.Text(parent, wrap=tk.WORD, state=tk.DISABLED)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

    def _build_alerts_panel(self, parent: ttk.Frame) -> None:
        controls = ttk.Frame(parent)
        controls.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(controls, text="Refresh", command=self.refresh_alerts).pack(side=tk.LEFT)

        self.alerts_text = tk.Text(parent, wrap=tk.WORD, state=tk.DISABLED)
        self.alerts_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

    def _build_history_panel(self, parent: ttk.Frame) -> None:
        controls = ttk.Frame(parent)
        controls.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(controls, text="Refresh", command=self.refresh_history).pack(side=tk.LEFT)

        self.history_text = tk.Text(parent, wrap=tk.WORD, state=tk.DISABLED)
        self.history_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

    def _build_settings_panel(self, parent: ttk.Frame) -> None:
        form = ttk.Frame(parent)
        form.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self._add_setting(form, "Monitoring thresholds", "CPU/RAM/Disk threshold placeholders")
        self._add_setting(form, "Polling interval", "5 seconds (placeholder)")
        self._add_setting(form, "Trusted apps/paths", "Placeholder allowlist editor")
        self._add_setting(form, "High-risk actions", "Disabled (placeholder toggle)")

        voice_frame = ttk.LabelFrame(form, text="Voice (offline)")
        voice_frame.pack(fill=tk.X, pady=10)

        self.stt_enabled_var = tk.BooleanVar(value=self.voice.settings.stt_enabled)
        self.tts_enabled_var = tk.BooleanVar(value=self.voice.settings.tts_enabled)
        self.push_to_talk_var = tk.BooleanVar(value=self.voice.settings.push_to_talk)

        ttk.Checkbutton(voice_frame, text="STT enabled", variable=self.stt_enabled_var, command=self._sync_voice_settings).pack(anchor=tk.W, padx=8, pady=2)
        ttk.Checkbutton(voice_frame, text="TTS enabled", variable=self.tts_enabled_var, command=self._sync_voice_settings).pack(anchor=tk.W, padx=8, pady=2)
        ttk.Checkbutton(voice_frame, text="Push-to-talk", variable=self.push_to_talk_var, command=self._sync_voice_settings).pack(anchor=tk.W, padx=8, pady=2)
        self._add_setting(voice_frame, "Input device", self.voice.settings.input_device)
        self._add_setting(voice_frame, "Output voice", self.voice.settings.output_voice)

    @staticmethod
    def _add_setting(parent: ttk.Frame, label: str, value: str) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text=label, width=24).pack(side=tk.LEFT)
        ttk.Entry(row).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(row, text=value, foreground="gray").pack(side=tk.LEFT, padx=8)

    def _sync_voice_settings(self) -> None:
        if self.stt_enabled_var is not None:
            self.voice.settings.stt_enabled = self.stt_enabled_var.get()
        if self.tts_enabled_var is not None:
            self.voice.settings.tts_enabled = self.tts_enabled_var.get()
        if self.push_to_talk_var is not None:
            self.voice.settings.push_to_talk = self.push_to_talk_var.get()

    def _send_chat(self) -> None:
        if self.chat_input is None:
            return
        text = self.chat_input.get().strip()
        if not text:
            return
        self.chat_input.delete(0, tk.END)
        self._submit_user_text(text)

    def _submit_user_text(self, text: str) -> None:
        self._append_chat("You", text)

        response = self.orchestrator.handle_request(text)
        if response.status == "confirmation_required" and response.action_id:
            approved = self._confirm_medium_risk(response)
            response = self.orchestrator.confirm_action(response.action_id, approved)

        self._append_structured_response(response)
        self.voice.speak_response(response.message)
        self.refresh_all()

    def _start_recording(self) -> None:
        result = self.voice.start_recording()
        if result.error:
            self._set_recording_state(f"Mic error: {result.error}")
            return
        self._set_recording_state("Mic: recording...")

    def _stop_recording(self) -> None:
        result = self.voice.stop_recording_and_transcribe()
        if result.error:
            self._set_recording_state(f"Mic error: {result.error}")
            self._set_transcription(result.error)
            return

        self._set_recording_state("Mic: idle")
        if not result.transcription:
            self._set_transcription("(empty transcription)")
            return

        self._set_transcription(result.transcription)
        if self.chat_input is not None:
            self.chat_input.delete(0, tk.END)
            self.chat_input.insert(0, result.transcription)
        self._submit_user_text(result.transcription)

    def _set_recording_state(self, value: str) -> None:
        if self.recording_state_var is not None:
            self.recording_state_var.set(value)

    def _set_transcription(self, value: str) -> None:
        if self.transcription_var is not None:
            self.transcription_var.set(f"Last transcription: {value}")

    def _confirm_medium_risk(self, response: AgentResponse) -> bool:
        return messagebox.askyesno(
            "Permission confirmation",
            f"This is a medium-risk action:\n\n{response.action}\n\nDo you want to continue?",
            parent=self.root,
        )

    def _append_chat(self, sender: str, message: str) -> None:
        if self.chat_output is None:
            return
        self.chat_output.configure(state=tk.NORMAL)
        self.chat_output.insert(tk.END, f"{sender}: {message}\n")
        self.chat_output.configure(state=tk.DISABLED)
        self.chat_output.see(tk.END)

    def _append_structured_response(self, response: AgentResponse) -> None:
        payload = {
            "status": response.status,
            "message": response.message,
            "action": response.action,
            "data": response.data,
        }
        self._append_chat("Assistant", json.dumps(payload, indent=2, default=str))

    def refresh_all(self) -> None:
        self.refresh_status()
        self.refresh_alerts()
        self.refresh_history()

    def refresh_status(self) -> None:
        status = self.monitoring.current_system_status()
        self._set_text(self.status_text, json.dumps(status, indent=2, default=str))

    def refresh_alerts(self) -> None:
        alerts = self.monitoring.list_alerts(limit=50)
        rendered = "\n\n".join(json.dumps(alert, indent=2, default=str) for alert in alerts) or "No alerts."
        self._set_text(self.alerts_text, rendered)

    def refresh_history(self) -> None:
        events = self.audit_logger.list_events(limit=100)
        rendered = "\n\n".join(json.dumps(event, indent=2, default=str) for event in events) or "No history yet."
        self._set_text(self.history_text, rendered)

    @staticmethod
    def _set_text(widget: tk.Text | None, value: str) -> None:
        if widget is None:
            return
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, value)
        widget.configure(state=tk.DISABLED)
