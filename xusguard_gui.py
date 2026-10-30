#!/usr/bin/env python3
"""XusGuard Desktop: local, standard-library Tkinter GUI.

Visual design adapted from the owner's AnonEngine UI palette and sidebar.
No web server, remote JavaScript, browser APIs, or automatic elevation.
"""
import hashlib
import queue
import subprocess
import sys
import threading
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import messagebox, simpledialog, scrolledtext
except ImportError as exc:
    raise SystemExit("Tkinter is required. Install your OS's python3-tk package.") from exc

import xusguard as core
from xusguard_preview import apply_preview, build_preview

BACKGROUND = "#070608"
SIDEBAR = "#09080b"
SURFACE = "#0f0c11"
LINE = "#241117"
RED = "#ff2238"
TEXT = "#f5f5f7"
MUTED = "#b7a7af"
GREEN = "#73dba0"


class XusGuardDesktop:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("XusGuard | Hosts Control")
        self.root.geometry("1100x730")
        self.root.minsize(880, 580)
        self.root.configure(bg=BACKGROUND)
        self.jobs = queue.Queue()
        self.busy = False
        self.sources = core.load_sources()
        self.preview = None
        self.records = []
        self.current_view = "Dashboard"

        self.sidebar = tk.Frame(self.root, bg=SIDEBAR, width=235)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg=SIDEBAR, padx=22, pady=26)
        brand.pack(fill="x")
        tk.Label(brand, text="XUS  /  GUARD", bg=SIDEBAR, fg=TEXT,
                 font=("Segoe UI", 19, "bold")).pack(anchor="w")
        tk.Label(brand, text="HOSTS SECURITY CONSOLE", bg=SIDEBAR, fg=RED,
                 font=("Consolas", 9)).pack(anchor="w", pady=(4, 0))
        tk.Frame(self.sidebar, bg=LINE, height=1).pack(fill="x", padx=14, pady=(5, 14))
        self.nav_buttons = {}
        for name in ("Dashboard", "Blocklists", "Preview & Apply", "Services",
                     "Recovery", "Diagnostics"):
            btn = tk.Button(self.sidebar, text="  " + name, anchor="w",
                            relief="flat", bd=0, bg=SIDEBAR, fg=MUTED,
                            activebackground=SURFACE, activeforeground=TEXT,
                            font=("Segoe UI", 11), padx=15, pady=12,
                            command=lambda name=name: self.show(name))
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[name] = btn
        tk.Label(self.sidebar, text="LOCAL ONLY  •  NO AUTO-ELEVATION",
                 bg=SIDEBAR, fg=MUTED, font=("Consolas", 8), wraplength=190
                 ).pack(side="bottom", pady=22)

        self.main = tk.Frame(self.root, bg=BACKGROUND, padx=26, pady=22)
        self.main.pack(side="left", fill="both", expand=True)
        self.header = tk.Frame(self.main, bg=BACKGROUND)
        self.header.pack(fill="x")
        self.title = tk.Label(self.header, bg=BACKGROUND, fg=TEXT,
                              font=("Segoe UI", 22, "bold"))
        self.title.pack(side="left")
        self.status = tk.Label(self.header, text="LOCAL", bg=SURFACE, fg=GREEN,
                               padx=12, pady=7, font=("Consolas", 10))
        self.status.pack(side="right")
        tk.Frame(self.main, bg=LINE, height=1).pack(fill="x", pady=16)
        self.area = tk.Frame(self.main, bg=BACKGROUND)
        self.area.pack(fill="both", expand=True)
        self.footer = tk.Label(self.main, text="Ready. Changes require explicit confirmation.",
                               bg=BACKGROUND, fg=MUTED, anchor="w",
                               font=("Consolas", 9))
        self.footer.pack(fill="x", pady=(9, 0))
        self.show("Dashboard")
        self.root.after(160, self.poll_jobs)

    def label(self, parent, text, *, size=10, color=MUTED, bold=False, pady=5):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("Segoe UI", size, "bold" if bold else "normal"),
                        justify="left", anchor="w", wraplength=720,
                        pady=pady)

    def button(self, parent, text, action, *, primary=False):
        b = tk.Button(parent, text=text, command=action, bg=RED if primary else SURFACE,
                      fg=TEXT, activebackground="#e02037",
                      activeforeground=TEXT, relief="flat", bd=0,
                      font=("Segoe UI", 10, "bold"), padx=14, pady=10,
                      cursor="hand2")
        b.pack(side="left", padx=(0, 10), pady=8)
        return b

    def controls(self):
        return tk.Frame(self.area, bg=BACKGROUND)

    def note(self, text, color=MUTED):
        self.footer.configure(text=text, fg=color)

    def show(self, name):
        self.current_view = name
        self.preview = None if name != "Preview & Apply" else self.preview
        for child in self.area.winfo_children():
            child.destroy()
        self.title.configure(text=name.upper())
        for key, item in self.nav_buttons.items():
            item.configure(bg=SURFACE if key == name else SIDEBAR,
                           fg=TEXT if key == name else MUTED,
                           highlightbackground=RED if key == name else SIDEBAR)
        getattr(self, "show_" + name.lower().replace(" & ", "_").replace(" ", "_"))()

    def text_box(self, parent, height=14):
        box = scrolledtext.ScrolledText(parent, bg=SURFACE, fg=TEXT,
                                       insertbackground=TEXT, selectbackground="#5e202d",
                                       relief="flat", bd=0, height=height,
                                       font=("Consolas", 10), padx=12, pady=12,
                                       wrap="word")
        box.pack(fill="both", expand=True, pady=10)
        return box

    def listbox(self, parent, height=14):
        lb = tk.Listbox(parent, bg=SURFACE, fg=TEXT, selectbackground="#5e202d",
                        selectforeground=TEXT, bd=0, relief="flat",
                        highlightthickness=1, highlightbackground=LINE,
                        font=("Consolas", 10), activestyle="none", height=height)
        lb.pack(fill="both", expand=True, pady=10)
        return lb

    def show_dashboard(self):
        self.label(self.area, "Ad-blocking status is based on local hosts-file rules, not on a remote server.",
                   size=11).pack(fill="x")
        target = Path(core.get_hosts_file_path())
        panel = tk.Frame(self.area, bg=SURFACE, padx=22, pady=18)
        panel.pack(fill="x", pady=15)
        self.label(panel, "SYSTEM HOSTS FILE", color=RED, bold=True).pack(fill="x")
        self.label(panel, str(target), color=TEXT, size=12).pack(fill="x")
        try:
            raw = target.read_bytes()
            content = raw.decode("utf-8", errors="replace")
            _, managed = core.split_managed_section(content)
            managed_count = len(core.parse_hosts_file(managed))
            services = len(core.get_service_blocked_domains(content))
            backups = len(core.get_available_backups(str(target)))
            summary = f"Blocklist rules: {managed_count:,}     Service rules: {services:,}     Verified backups: {backups}"
            self.status.configure(text="RULES PRESENT" if managed_count or services else "NO RULES")
            self.label(panel, summary, color=GREEN if managed_count or services else MUTED,
                       size=11).pack(fill="x", pady=(14, 0))
        except (OSError, ValueError) as exc:
            self.status.configure(text="UNAVAILABLE", fg=RED)
            self.label(panel, f"Unable to inspect hosts: {exc}", color=RED).pack(fill="x")
        actions = self.controls()
        actions.pack(fill="x")
        self.button(actions, "Create backup", self.create_backup, primary=True)
        self.button(actions, "Recovery drill", self.run_recovery_drill)
        self.button(actions, "Open recovery", lambda: self.show("Recovery"))
        self.label(self.area, "Recommended flow: choose lists → download → preview → apply. "
                   "Rollback is always one click away under Recovery, followed by confirmation.",
                   size=11).pack(fill="x", pady=18)

    def show_blocklists(self):
        self.label(self.area, "All sources are opt-in. Toggle a source, save your choices, "
                   "then download verified HTTPS lists without changing the system hosts file.",
                   size=11).pack(fill="x")
        self.sources_list = self.listbox(self.area)
        self.refresh_sources_list()
        actions = self.controls()
        actions.pack(fill="x")
        self.button(actions, "Toggle selected", self.toggle_source)
        self.button(actions, "Save choices", self.save_sources, primary=True)
        self.button(actions, "Download enabled", self.download_enabled)
        self.label(self.area, "Downloaded lists are cached locally. Preview & Apply is a separate, "
                   "explicit operation. No downloads run automatically.", size=10).pack(fill="x")

    def refresh_sources_list(self):
        self.source_keys = sorted(self.sources, key=lambda n: int(n))
        if not hasattr(self, "sources_list"):
            return
        self.sources_list.delete(0, "end")
        for key in self.source_keys:
            src = self.sources[key]
            on = "ON " if src.get("enabled") else "OFF"
            self.sources_list.insert("end", f"[{on}] {src['name']} — {src['url']}")

    def toggle_source(self):
        idx = self.sources_list.curselection()
        if not idx:
            return
        key = self.source_keys[idx[0]]
        self.sources[key]["enabled"] = not self.sources[key]["enabled"]
        self.refresh_sources_list()
        self.sources_list.selection_set(idx[0])
        self.note("Unsaved choices. Use Save choices before downloading or applying.")

    def save_sources(self):
        if core.save_sources(self.sources):
            self.sources = core.load_sources()
            self.preview = None
            self.note("Source choices saved.", GREEN)
        else:
            messagebox.showerror("Save failed", "Your sources.json was not changed.")

    def background(self, label, work):
        if self.busy:
            self.note("Another operation is already running.")
            return
        self.busy = True
        self.note(label + " …")
        def runner():
            try:
                result = work()
                self.jobs.put((True, label, result))
            except Exception as exc:
                self.jobs.put((False, label, f"{type(exc).__name__}: {exc}"))
        threading.Thread(target=runner, daemon=True).start()

    def poll_jobs(self):
        try:
            while True:
                ok, label, result = self.jobs.get_nowait()
                self.busy = False
                self.note(f"{label}: {result}", GREEN if ok else RED)
                if label == "Recovery drill":
                    self.show("Diagnostics")
                    self.diagnostics_out.insert("end", str(result))
                elif not ok:
                    messagebox.showerror(label, str(result))
        except queue.Empty:
            pass
        self.root.after(160, self.poll_jobs)

    def download_enabled(self):
        if not self.save_sources_silent():
            return
        selected = [dict(src) for src in self.sources.values() if src["enabled"]]
        if not selected:
            messagebox.showinfo("No sources", "Enable at least one source first.")
            return
        def work():
            details = []
            for source in selected:
                raw = core.download_hosts_file(source["url"], timeout=30)
                if raw is None:
                    details.append(source["name"] + ": failed")
                    continue
                items = core.parse_hosts_file(raw)
                merged, _ = core.merge_hosts_entries([items])
                stored = core.save_source_file(None, source["name"], merged) if merged else None
                details.append(f"{source['name']}: {len(merged):,} domains" if stored
                               else source["name"] + ": rejected")
            return " | ".join(details)
        self.background("Download enabled", work)

    def save_sources_silent(self):
        if not core.save_sources(self.sources):
            messagebox.showerror("Save sources", "Could not safely save sources.json.")
            return False
        return True

    def show_preview_apply(self):
        self.label(self.area, "No hosts-file changes happen until you approve Apply. "
                   "The preview is rebuilt and compared before installation.", size=11).pack(fill="x")
        actions = self.controls()
        actions.pack(fill="x")
        self.button(actions, "Build preview", self.build_preview, primary=True)
        self.button(actions, "Apply verified preview", self.apply_hosts)
        self.preview_text = self.text_box(self.area, height=18)
        self.preview_text.insert("end", "Select and save sources, download them, then click Build preview.\n")
        self.preview_text.configure(state="disabled")

    def build_preview(self):
        try:
            self.preview = build_preview(core, core.get_hosts_file_path(),
                                         core.load_sources())
            p = self.preview
            excerpt = "\n".join(p["content"].splitlines()[:75])
            detail = (f"Sources: {', '.join(p['sources'])}\n"
                      f"Unique domains: {p['domains']:,}\n"
                      f"Original SHA-256: {p['original_sha256']}\n"
                      f"Proposed SHA-256: {p['new_sha256']}\n"
                      f"\nFirst 75 lines of resulting hosts file:\n\n{excerpt}\n"
                      "\n… preview truncated for display; apply uses the full result.")
            self.preview_text.configure(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("end", detail)
            self.preview_text.configure(state="disabled")
            self.note("Preview built. Recomputed at Apply to prevent stale writes.", GREEN)
        except (OSError, ValueError, UnicodeError) as exc:
            self.preview = None
            messagebox.showerror("Preview rejected", str(exc))

    def apply_hosts(self):
        if self.preview is None:
            messagebox.showwarning("Build preview", "Build a preview before applying.")
            return
        p = self.preview
        if not messagebox.askyesno("Apply hosts change",
            f"Apply {p['domains']:,} domains from {len(p['sources'])} lists?\n\n"
            "XusGuard will create a mandatory backup. This changes system-wide DNS."):
            return
        try:
            if not apply_preview(core, p, core.load_sources()):
                raise OSError("The hosts file was not changed. Check permissions and backups.")
            self.preview = None
            self.note("Verified hosts change installed; rollback is available under Recovery.", GREEN)
            messagebox.showinfo("Applied", "Hosts change completed. A safety backup was created.")
        except (OSError, ValueError, UnicodeError) as exc:
            self.preview = None
            messagebox.showerror("Apply refused", str(exc))

    def show_services(self):
        self.label(self.area, "Optional access blocking: selecting a service can prevent its "
                   "website or app from working. Downloaded blocklists are kept separate.",
                   size=11).pack(fill="x")
        try:
            self.catalog_categories, self.catalog = core.load_service_catalog()
            self.service_order = list(self.catalog.keys())
            self.service_list = self.listbox(self.area)
            target = Path(core.get_hosts_file_path())
            content = target.read_text(encoding="utf-8", errors="replace")
            enabled = core.get_service_blocked_domains(content)
            for key in self.service_order:
                s = self.catalog[key]
                count = len(set(s["domains"]) & enabled)
                status = "ON" if count == len(s["domains"]) else ("PARTIAL" if count else "OFF")
                self.service_list.insert("end", f"[{status}] {s['category']} / {s['name']}")
            actions = self.controls()
            actions.pack(fill="x")
            self.button(actions, "Block selected", lambda: self.set_service(True), primary=True)
            self.button(actions, "Unblock selected", lambda: self.set_service(False))
        except (OSError, ValueError) as exc:
            self.label(self.area, f"Services unavailable: {exc}", color=RED).pack(fill="x")

    def set_service(self, enabled):
        idx = self.service_list.curselection()
        if not idx:
            return
        service = self.catalog[self.service_order[idx[0]]]
        verb = "BLOCK" if enabled else "UNBLOCK"
        if not messagebox.askyesno(f"{verb} {service['name']}",
          f"{verb} {service['name']} ({len(service['domains'])} domains)?\n"
          "This may interrupt connectivity and requires a safety backup."):
            return
        domains = {d: "0.0.0.0" for d in service["domains"]}
        if core.apply_service_changes(core.get_hosts_file_path(), domains, enabled, service["name"]):
            self.show("Services")
            self.note(f"{service['name']} rules updated.", GREEN)
        else:
            messagebox.showerror("Failed", "Service rules were not changed.")

    def show_recovery(self):
        self.label(self.area, "Recovery only accepts matching, regular backup files from "
                   "trusted directories. It verifies a SHA-256 before writing exact original bytes.",
                   size=11).pack(fill="x")
        self.recovery_list = self.listbox(self.area, height=12)
        self.reload_backups()
        buttons = self.controls()
        buttons.pack(fill="x")
        self.button(buttons, "Create backup", self.create_backup, primary=True)
        self.button(buttons, "Refresh", self.reload_backups)
        self.button(buttons, "Inspect selected", self.inspect_backup)
        self.button(buttons, "Restore selected", self.restore_backup)
        self.recovery_info = self.text_box(self.area, height=6)
        self.recovery_info.insert("end", "Choose a verified backup to see its size and SHA-256.")
        self.recovery_info.configure(state="disabled")

    def reload_backups(self):
        try:
            self.records = core.get_available_backups(core.get_hosts_file_path())
            self.recovery_list.delete(0, "end")
            for item in self.records:
                self.recovery_list.insert("end",
                    f"{item['created']}  {item['size']:>8,} bytes  {Path(item['path']).name}")
        except (OSError, ValueError) as exc:
            self.records = []
            self.note(f"Cannot list backups: {exc}", RED)

    def chosen_backup(self):
        selected = self.recovery_list.curselection()
        if not selected:
            messagebox.showinfo("Select backup", "Choose a backup first.")
            return None
        return self.records[selected[0]]

    def inspect_backup(self):
        item = self.chosen_backup()
        if item is None:
            return
        self.recovery_info.configure(state="normal")
        self.recovery_info.delete("1.0", "end")
        self.recovery_info.insert("end", f"Path: {item['path']}\n"
                                  f"Size: {item['size']:,} bytes\n"
                                  f"SHA-256: {item['sha256']}\n"
                                  f"Created: {item['created']}\n"
                                  "Restore makes another safety backup first.")
        self.recovery_info.configure(state="disabled")

    def restore_backup(self):
        item = self.chosen_backup()
        if item is None:
            return
        if not messagebox.askyesno("Recovery", "Restore this verified backup?\n"
          "Current DNS mappings will be replaced. A safety backup is mandatory."):
            return
        confirm = simpledialog.askstring("Confirm recovery",
            "Type RESTORE to confirm exact-byte rollback:", parent=self.root)
        if confirm != "RESTORE":
            self.note("Recovery cancelled.")
            return
        if core.recover_selected_backup(core.get_hosts_file_path(),
                                        item["path"], item["sha256"]):
            self.show("Recovery")
            self.note("Verified restore complete. Previous file backed up.", GREEN)
            messagebox.showinfo("Recovery complete", "Hosts file successfully restored.")
        else:
            messagebox.showerror("Recovery refused", "No change made; check backup and permissions.")

    def create_backup(self):
        if core.backup_hosts_file(core.get_hosts_file_path()):
            self.note("Safety backup created.", GREEN)
            if self.current_view == "Recovery":
                self.reload_backups()
        else:
            messagebox.showerror("Backup failed", "Could not create a verified hosts backup.")

    def show_diagnostics(self):
        self.label(self.area, "Recovery drill operates on temporary test files only, "
                   "not your system hosts file. No network access is needed.", size=11).pack(fill="x")
        actions = self.controls()
        actions.pack(fill="x")
        self.button(actions, "Run recovery drill", self.run_recovery_drill, primary=True)
        self.diagnostics_out = self.text_box(self.area, height=22)
        self.diagnostics_out.insert("end", "Click Run recovery drill to launch automated safety tests.")

    def run_recovery_drill(self):
        folder = Path(__file__).resolve().parent
        def run():
            completed = subprocess.run(
                [sys.executable, "-m", "unittest", "discover",
                 "-s", "tests", "-p", "test_recovery.py", "-v"],
                cwd=str(folder), capture_output=True, text=True, timeout=120,
                check=False)
            result = (completed.stdout + "\n" + completed.stderr)[-11000:]
            if completed.returncode:
                raise RuntimeError("Recovery drill FAILED:\n" + result)
            return "Recovery drill PASS:\n" + result
        self.background("Recovery drill", run)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    XusGuardDesktop().run()
