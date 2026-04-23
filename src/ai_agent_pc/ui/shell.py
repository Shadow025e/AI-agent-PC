"""Desktop UI shell for the local MVP (offline-only)."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk

from ai_agent_pc.db.sqlite import AuditLogger
from ai_agent_pc.monitoring.service import MonitoringService
from ai_agent_pc.orchestrator.agent_orchestrator import AgentOrchestrator, AgentResponse


class UIShell:
    """Minimal desktop UI with chat + status + alerts + history + settings."""

    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        monitoring: MonitoringService,
        audit_logger: AuditLogger,
    ) -> None:
        self.orchestrator = orchestrator
        self.monitoring = monitoring
        self.audit_logger = audit_logger
        self.root: tk.Tk | None = None

        self.chat_output: tk.Text | None = None
        self.chat_input: tk.Entry | None = None
        self.status_text: tk.Text | None = None
        self.alerts_text: tk.Text | None = None
        self.history_text: tk.Text | None = None
        self.offline_var: tk.StringVar | None = None

    def render_welcome(self) -> None:
        self.root = tk.Tk()
        self.root.title("AI Agent PC - Offline MVP")
        self.root.geometry("1080x720")

        self.offline_var = tk.StringVar(value="● Offline Mode")

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
        self._add_setting(form, "Voice", "Not enabled in this step")

    @staticmethod
    def _add_setting(parent: ttk.Frame, label: str, value: str) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text=label, width=24).pack(side=tk.LEFT)
        ttk.Entry(row).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(row, text=value, foreground="gray").pack(side=tk.LEFT, padx=8)

    def _send_chat(self) -> None:
        if self.chat_input is None:
            return
        text = self.chat_input.get().strip()
        if not text:
            return
        self.chat_input.delete(0, tk.END)
        self._append_chat("You", text)

        response = self.orchestrator.handle_request(text)
        if response.status == "confirmation_required" and response.action_id:
            approved = self._confirm_medium_risk(response)
            response = self.orchestrator.confirm_action(response.action_id, approved)

        self._append_structured_response(response)
        self.refresh_all()

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
