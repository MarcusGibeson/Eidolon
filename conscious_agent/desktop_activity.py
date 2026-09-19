"""Native read-only Activity rail and inspector using the same web/API contract."""
from __future__ import annotations

from threading import Thread
import tkinter as tk
from tkinter import ttk

CONTRACT = "activity.v1"


def summary_lines(row):
    p, g = row.get("progress") or {}, row.get("governance") or {}
    lines = [str(row.get("state", "unknown")).upper(), str(row.get("title", "")), str(row.get("type", "")),
             str(row.get("subject", "")), str(row.get("stage") or "Queued"),
             f"{p.get('completed', 0)} / {p.get('total') if p.get('total') is not None else '?'} {p.get('unit', 'units')}"]
    seconds = row.get("elapsed_seconds")
    lines.append(f"{seconds // 60}m {seconds % 60}s elapsed" if seconds is not None else "Elapsed unknown")
    if g.get("read_only") is True:
        lines.append("READ ONLY")
    if g.get("non_authoritative") is True:
        lines.append("NON-AUTHORITATIVE")
    if g.get("belief_effects") == "none":
        lines.append("BELIEF EFFECTS NONE")
    if g.get("mutation_guard"):
        lines.append("MUTATION GUARD: " + str(g["mutation_guard"]))
    lines += [str(w).replace("_", " ") for w in row.get("warnings", [])]
    if row.get("reason"):
        lines.append(str(row["reason"]).replace("_", " "))
    lines += [f"{k.replace('_', ' ')}: {v}" for k, v in row.get("metrics", {}).items()]
    return lines


def detail_text(row):
    lines = summary_lines(row) + ["", "STAGES"]
    lines += [f"{s['name']}: {s['state']}" for s in row.get("stages", [])]
    stage = row.get("stage_progress") or {}
    if stage:
        lines.append(f"Stage: {stage.get('completed', 0)} / {stage.get('total') if stage.get('total') is not None else '?'} {stage.get('unit', 'units')}")
    lines += ["", "WORK BREAKDOWN"]
    lines += [f"{p['id']} {p['label']}: {p['completed']} / {p['total']}" for p in row.get("breakdown", [])]
    lines += ["", "IDENTITY", "activity_id: " + str(row.get("activity_id", ""))]
    lines += [f"{k}: {v}" for k, v in row.get("identities", {}).items()]
    lines += ["Result: " + str(row.get("result", "")), "", "OPERATIONAL EVENTS"]
    if row.get("events_omitted"):
        lines.append(f"{row['events_omitted']} older events outside retained window")
    lines += [f"{e['at']} #{e['sequence']} {e['event']} - {e['stage']}" for e in reversed(row.get("events", []))]
    return "\n".join(lines)


class ActivityPanel:
    def __init__(self, root, parent, client, colors):
        self.root, self.client, self.colors = root, client, colors
        self.busy = False
        self.closed = False
        self.payload = {"activities": []}
        self.window = None
        self.selected = None
        self.frame = tk.Frame(parent, width=290, background=colors["surface"], padx=12, pady=12)
        self.frame.pack(side="right", fill="y", padx=(0, 12))
        self.frame.pack_propagate(False)
        tk.Label(self.frame, text="CURRENT ACTIVITY", background=colors["surface"], foreground=colors["cyan"],
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.state = tk.StringVar(value="Checking activity...")
        from tkinter.scrolledtext import ScrolledText
        self.body = ScrolledText(self.frame, height=20, width=26, wrap="word", relief="flat",
                                 background=colors["surface"], foreground=colors["text"], font=("Segoe UI", 10))
        self.body.pack(fill="both", expand=True, pady=12)
        def sync_text(*_):
            self.body.configure(state="normal")
            self.body.delete("1.0", "end")
            self.body.insert("end", self.state.get())
            self.body.configure(state="disabled")
        self.state.trace_add("write", sync_text)
        sync_text()
        self.bar = ttk.Progressbar(self.frame, maximum=100)
        self.bar.pack(fill="x")
        tk.Button(self.frame, text="Activity details and history", command=self.open,
                  background=colors["surface_raised"], foreground=colors["text"], relief="flat").pack(fill="x", pady=12)
        root.bind("<Destroy>", self._destroyed, add="+")
        self.poll()

    def _destroyed(self, event):
        if event.widget is self.root:
            self.closed = True

    def poll(self):
        if self.closed:
            return
        if not self.busy:
            self.busy = True
            def fetch():
                try:
                    envelope = self.client.get("/activities", timeout=4)
                    data = envelope.get("data", envelope)
                    if data.get("contract") != CONTRACT:
                        raise ValueError("activity_contract_mismatch")
                    callback = lambda: self.render(data)
                except Exception:
                    callback = lambda: self.state.set("Activity unavailable. Displayed data may be stale.")
                finally:
                    self.busy = False
                if not self.closed:
                    try:
                        self.root.after(0, callback)
                    except RuntimeError:
                        pass
            Thread(target=fetch, daemon=True).start()
        self.root.after(3000, self.poll)

    def render(self, data):
        self.payload = data
        rows = data.get("activities", [])
        row = data.get("current") or (rows[0] if rows else None)
        self.state.set(("ACTIVE\n" if data.get("current") else "No active work\n") +
                       ("\n".join(summary_lines(row)) if row else "No activity recorded"))
        self.bar["value"] = (row.get("progress", {}).get("percent") or 0) if row else 0
        if self.window and self.window.winfo_exists():
            self.history.delete(0, "end")
            for r in rows:
                self.history.insert("end", f"{r['subject']} - {r['state']}")
            self.show_selected()

    def open(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return
        self.window = tk.Toplevel(self.root)
        self.window.title("Eidolon Activity")
        self.window.geometry("900x680")
        self.history = tk.Listbox(self.window, width=35, exportselection=False)
        self.history.pack(side="left", fill="y")
        from tkinter.scrolledtext import ScrolledText
        self.text = ScrolledText(self.window, wrap="word", background=self.colors["background"],
                                 foreground=self.colors["text"], font=("Segoe UI", 10))
        self.text.pack(fill="both", expand=True)
        def select(_):
            indices = self.history.curselection()
            if indices:
                self.selected = self.payload["activities"][indices[0]]["activity_id"]
                self.show_selected()
        self.history.bind("<<ListboxSelect>>", select)
        self.render(self.payload)

    def show_selected(self):
        rows = self.payload.get("activities", [])
        row = next((r for r in rows if r["activity_id"] == self.selected), rows[0] if rows else None)
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", detail_text(row) if row else "No activity recorded.")
        self.text.configure(state="disabled")
