"""Tkinter GUI for Ocrolus Automations (tabbed: Bulk Upload + Transfer Book)."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import keyring

from ocrolus_automations.automations.bulk_upload import (
    BulkUploadResult,
    format_summary,
    run_bulk_upload,
)
from ocrolus_automations.automations.move_book import (
    MoveBookResult,
    extract_docs_from_status,
    run_move_book,
)
from ocrolus_automations.clients.ocrolus_client import OcrolusClient
from ocrolus_automations.config import OrgCredentials
from ocrolus_automations.log_config import setup_logging
from ocrolus_automations.utils.env_store import add_org, parse_org_names

APP_NAME = "Ocrolus Automations"

# ---------------------------------------------------------------------------
# Keyring helpers (for Transfer Book tab — legacy credential store)
# ---------------------------------------------------------------------------

_KR_SERVICE = "Transfer Book Automation"


def _kr_key(org: str, field: str) -> str:
    return f"{org.lower().strip()}.{field}"


def load_credential(org: str, field: str) -> str:
    return keyring.get_password(_KR_SERVICE, _kr_key(org, field)) or ""


def save_credential(org: str, field: str, value: str) -> None:
    if not value:
        return
    keyring.set_password(_KR_SERVICE, _kr_key(org, field), value)


def clear_credentials(orgs: list[str]) -> None:
    for org in orgs:
        for field in ("client_id", "client_secret"):
            try:
                keyring.delete_password(_KR_SERVICE, _kr_key(org, field))
            except keyring.errors.PasswordDeleteError:
                continue


# ---------------------------------------------------------------------------
# Add-Org dialog
# ---------------------------------------------------------------------------


class AddOrgDialog(tk.Toplevel):
    """Modal dialog to add a new org's credentials."""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.title("Add Org Credentials")
        self.geometry("420x200")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result: tuple[str, str, str] | None = None

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        self.name_var = tk.StringVar()
        self.id_var = tk.StringVar()
        self.secret_var = tk.StringVar()

        ttk.Label(frame, text="Org Name").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.name_var).grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=4)

        ttk.Label(frame, text="Client ID").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.id_var).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=4)

        ttk.Label(frame, text="Client Secret").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.secret_var, show="*").grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=4)

        frame.columnconfigure(1, weight=1)

        btn_row = ttk.Frame(frame)
        btn_row.grid(row=3, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(btn_row, text="Save", command=self._on_save).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side="left", padx=4)

    def _on_save(self) -> None:
        name = self.name_var.get().strip()
        cid = self.id_var.get().strip()
        secret = self.secret_var.get().strip()
        if not name or not cid or not secret:
            messagebox.showerror("Missing info", "All fields are required.", parent=self)
            return
        self.result = (name, cid, secret)
        self.destroy()


# ---------------------------------------------------------------------------
# Bulk Upload tab
# ---------------------------------------------------------------------------


class BulkUploadTab:
    """Bulk Upload automation UI, placed inside a parent frame."""

    def __init__(self, parent: ttk.Frame, app_queue: queue.Queue) -> None:
        self._queue = app_queue
        self._build(parent)

    def _build(self, parent: ttk.Frame) -> None:
        form = ttk.Frame(parent, padding=12)
        form.pack(fill="x")

        # --- Org selector ---
        row = 0
        ttk.Label(form, text="Org", font=("Helvetica", 12, "bold")).grid(
            row=row, column=0, sticky="w", pady=(0, 6)
        )
        row += 1

        org_row = ttk.Frame(form)
        org_row.grid(row=row, column=0, columnspan=2, sticky="ew", pady=2)

        self.org_var = tk.StringVar()
        self.org_combo = ttk.Combobox(
            org_row, textvariable=self.org_var, state="readonly", width=30
        )
        self.org_combo.pack(side="left")
        self._refresh_orgs()

        ttk.Button(org_row, text="+ Add Org", command=self._on_add_org).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(org_row, text="Refresh", command=self._refresh_orgs).pack(
            side="left", padx=(4, 0)
        )
        row += 1

        ttk.Separator(form).grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1

        # --- Input folder ---
        ttk.Label(form, text="Input Folder", font=("Helvetica", 12, "bold")).grid(
            row=row, column=0, sticky="w", pady=(0, 6)
        )
        row += 1

        folder_row = ttk.Frame(form)
        folder_row.grid(row=row, column=0, columnspan=2, sticky="ew", pady=2)

        self.folder_var = tk.StringVar()
        self.folder_entry = ttk.Entry(folder_row, textvariable=self.folder_var)
        self.folder_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(folder_row, text="Browse...", command=self._on_browse).pack(
            side="left", padx=(8, 0)
        )
        row += 1

        ttk.Separator(form).grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1

        # --- Options ---
        self.dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text="Dry Run (preview only)", variable=self.dry_run_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=4
        )
        row += 1

        # --- Run button ---
        btn_row = ttk.Frame(form)
        btn_row.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        self.run_button = ttk.Button(btn_row, text="Run Bulk Upload", command=self._on_run)
        self.run_button.pack(side="left")

        form.columnconfigure(1, weight=1)

        # --- Log area ---
        self.log_text = tk.Text(parent, height=14, wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=12, pady=(8, 12))

    def _refresh_orgs(self) -> None:
        orgs = parse_org_names()
        self.org_combo["values"] = orgs
        if orgs and not self.org_var.get():
            self.org_var.set(orgs[0])

    def _on_add_org(self) -> None:
        dlg = AddOrgDialog(self.org_combo.winfo_toplevel())
        self.org_combo.winfo_toplevel().wait_window(dlg)
        if dlg.result:
            name, cid, secret = dlg.result
            add_org(name, cid, secret)
            self._refresh_orgs()
            self.org_var.set(name.lower())
            self._log(f"Added org '{name}'.")

    def _on_browse(self) -> None:
        path = filedialog.askdirectory(title="Select folder containing book subfolders")
        if path:
            self.folder_var.set(path)

    def _on_run(self) -> None:
        org = self.org_var.get().strip()
        folder = self.folder_var.get().strip()
        if not org:
            messagebox.showerror("Missing info", "Select an org.")
            return
        if not folder:
            messagebox.showerror("Missing info", "Select an input folder.")
            return

        self.run_button.config(state="disabled")
        self._log("Starting bulk upload...")

        thread = threading.Thread(
            target=self._run_worker,
            args=(org, folder, self.dry_run_var.get()),
            daemon=True,
        )
        thread.start()

    def _run_worker(self, org: str, folder: str, dry_run: bool) -> None:
        try:
            result = run_bulk_upload(
                input_dirs=[folder],
                org=org,
                dry_run=dry_run,
                return_result=True,
            )
            summary = format_summary(result, dry_run=dry_run)
            self._queue.put(("bulk_log", summary))
            if not dry_run and isinstance(result, BulkUploadResult) and not result.success:
                self._queue.put(("bulk_log", "Some uploads failed. See summary above."))
        except Exception as exc:
            self._queue.put(("bulk_error", str(exc)))
        finally:
            self._queue.put(("bulk_done", None))

    def _log(self, message: str) -> None:
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def handle_queue(self, kind: str, data: object) -> None:
        """Handle queue items prefixed with 'bulk_'."""
        if kind == "bulk_log":
            self._log(str(data))
        elif kind == "bulk_error":
            messagebox.showerror("Error", str(data))
            self._log(f"Error: {data}")
        elif kind == "bulk_done":
            self.run_button.config(state="normal")


# ---------------------------------------------------------------------------
# Transfer Book tab (preserved from original GUI)
# ---------------------------------------------------------------------------


class TransferBookTab:
    """Transfer Book automation UI, placed inside a parent frame."""

    def __init__(self, parent: ttk.Frame, app_queue: queue.Queue) -> None:
        self._queue = app_queue
        self._build(parent)
        self._load_saved_credentials()

    def _build(self, parent: ttk.Frame) -> None:
        form = ttk.Frame(parent, padding=12)
        form.pack(fill="x")

        self.source_id_var = tk.StringVar()
        self.source_secret_var = tk.StringVar()
        self.target_id_var = tk.StringVar()
        self.target_secret_var = tk.StringVar()
        self.source_book_var = tk.StringVar()
        self.target_book_name_var = tk.StringVar()

        row = 0
        ttk.Label(form, text="Org 1 (Source Org)", font=("Helvetica", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        row += 1
        ttk.Label(form, text="Client ID").grid(row=row, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.source_id_var).grid(row=row, column=1, sticky="ew", padx=(8, 0))
        row += 1
        ttk.Label(form, text="Client Secret").grid(row=row, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.source_secret_var, show="*").grid(
            row=row, column=1, sticky="ew", padx=(8, 0)
        )
        row += 1
        ttk.Label(form, text="Source Book UUID").grid(row=row, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.source_book_var).grid(row=row, column=1, sticky="ew", padx=(8, 0))
        row += 1

        ttk.Separator(form).grid(row=row, column=0, columnspan=2, sticky="ew", pady=12)
        row += 1

        ttk.Label(form, text="Org 2 (Target Org)", font=("Helvetica", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        row += 1
        ttk.Label(form, text="Client ID").grid(row=row, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.target_id_var).grid(row=row, column=1, sticky="ew", padx=(8, 0))
        row += 1
        ttk.Label(form, text="Client Secret").grid(row=row, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.target_secret_var, show="*").grid(
            row=row, column=1, sticky="ew", padx=(8, 0)
        )
        row += 1

        ttk.Separator(form).grid(row=row, column=0, columnspan=2, sticky="ew", pady=12)
        row += 1

        ttk.Label(form, text="Transfer Details", font=("Helvetica", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        row += 1
        ttk.Label(form, text="Target Book Name").grid(row=row, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.target_book_name_var).grid(row=row, column=1, sticky="ew", padx=(8, 0))
        row += 1

        form.columnconfigure(1, weight=1)

        button_row = ttk.Frame(parent, padding=(12, 0))
        button_row.pack(fill="x")

        self.run_button = ttk.Button(button_row, text="Run Transfer", command=self._on_run)
        self.run_button.pack(side="left")

        self.clear_button = ttk.Button(button_row, text="Clear Saved Credentials", command=self._on_clear_creds)
        self.clear_button.pack(side="right")

        self.log_text = tk.Text(parent, height=8, wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=12, pady=(8, 12))

    def _load_saved_credentials(self) -> None:
        self.source_id_var.set(load_credential("org1", "client_id"))
        self.source_secret_var.set(load_credential("org1", "client_secret"))
        self.target_id_var.set(load_credential("org2", "client_id"))
        self.target_secret_var.set(load_credential("org2", "client_secret"))

    def _on_clear_creds(self) -> None:
        ok = messagebox.askyesno(
            "Confirm Clear",
            "This will remove saved credentials for the Source and Target orgs. Continue?",
        )
        if not ok:
            return
        clear_credentials(["org1", "org2"])
        self._log("Cleared saved credentials for Source and Target orgs.")

    def _validate(self) -> tuple[bool, str]:
        fields = {
            "Source client ID": self.source_id_var.get().strip(),
            "Source client secret": self.source_secret_var.get().strip(),
            "Target client ID": self.target_id_var.get().strip(),
            "Target client secret": self.target_secret_var.get().strip(),
            "Source book UUID": self.source_book_var.get().strip(),
            "Target book name": self.target_book_name_var.get().strip(),
        }
        for name, value in fields.items():
            if not value:
                return False, f"{name} is required."
        return True, ""

    def _on_run(self) -> None:
        ok, msg = self._validate()
        if not ok:
            messagebox.showerror("Missing info", msg)
            return

        self._save_credentials()
        self.run_button.config(state="disabled")
        self.clear_button.config(state="disabled")
        self._log("Starting transfer...")

        thread = threading.Thread(target=self._run_worker, daemon=True)
        thread.start()

    def _save_credentials(self) -> None:
        save_credential("org1", "client_id", self.source_id_var.get().strip())
        save_credential("org1", "client_secret", self.source_secret_var.get().strip())
        save_credential("org2", "client_id", self.target_id_var.get().strip())
        save_credential("org2", "client_secret", self.target_secret_var.get().strip())

    def _run_worker(self) -> None:
        try:
            source_org = "org1"
            target_org = "org2"
            creds = {
                source_org: OrgCredentials(
                    client_id=self.source_id_var.get().strip(),
                    client_secret=self.source_secret_var.get().strip(),
                ),
                target_org: OrgCredentials(
                    client_id=self.target_id_var.get().strip(),
                    client_secret=self.target_secret_var.get().strip(),
                ),
            }
            client = OcrolusClient(org_credentials=creds)

            self._queue.put(("xfer_log", "Validating source credentials and fetching book status..."))
            client.get_token(source_org)
            status = client.get_book_status(self.source_book_var.get().strip(), source_org)
            payload = status.get("response", status) if isinstance(status, dict) else status
            docs = extract_docs_from_status(payload)
            doc_count = len(docs)

            confirm_event = threading.Event()
            confirm_state = {"ok": False}
            confirm_msg = (
                f"This will create a new book in the Target Org and upload {doc_count} documents.\n\n"
                f"Target book name: {self.target_book_name_var.get().strip()}\n\n"
                "Continue?"
            )
            self._queue.put(("xfer_confirm", confirm_msg, confirm_event, confirm_state))
            confirm_event.wait()
            if not confirm_state["ok"]:
                self._queue.put(("xfer_log", "Transfer canceled."))
                self._queue.put(("xfer_done", None))
                return

            self._queue.put(("xfer_log", "Starting transfer..."))
            result = run_move_book(
                source_book_uuid=self.source_book_var.get().strip(),
                target_book_name=self.target_book_name_var.get().strip(),
                org_source=source_org,
                org_target=target_org,
                client=client,
                return_result=True,
            )
            self._queue.put(("xfer_result", result))
        except Exception as exc:
            self._queue.put(("xfer_error", str(exc)))
        finally:
            self._queue.put(("xfer_done", None))

    def _log(self, message: str) -> None:
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def handle_queue(self, kind: str, item: tuple) -> None:
        """Handle queue items prefixed with 'xfer_'."""
        if kind == "xfer_log":
            self._log(str(item))
        elif kind == "xfer_confirm":
            _, message, event, state = item  # item is the full tuple
            return  # handled specially in main app
        elif kind == "xfer_result":
            result: MoveBookResult = item
            if result.success:
                self._log("Transfer complete.")
            else:
                message = "Transfer failed."
                if result.created_target_book and result.target_book_uuid:
                    message += (
                        f"\n\nA new target book was created (UUID: {result.target_book_uuid})."
                        " Please delete this book before re-running."
                    )
                if result.failures:
                    message += "\n\nFailures:\n" + "\n".join(result.failures[:10])
                    if len(result.failures) > 10:
                        message += f"\n...and {len(result.failures) - 10} more"
                messagebox.showerror("Transfer failed", message)
                self._log("Transfer failed. See error dialog for details.")
        elif kind == "xfer_error":
            messagebox.showerror("Error", str(item))
            self._log(f"Error: {item}")
        elif kind == "xfer_done":
            self.run_button.config(state="normal")
            self.clear_button.config(state="normal")


# ---------------------------------------------------------------------------
# Main tabbed application
# ---------------------------------------------------------------------------


class OcrolusApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("700x600")
        self.root.minsize(640, 520)

        self._queue: queue.Queue = queue.Queue()

        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        bulk_frame = ttk.Frame(notebook)
        xfer_frame = ttk.Frame(notebook)
        notebook.add(bulk_frame, text="  Bulk Upload  ")
        notebook.add(xfer_frame, text="  Transfer Book  ")

        self.bulk_tab = BulkUploadTab(bulk_frame, self._queue)
        self.xfer_tab = TransferBookTab(xfer_frame, self._queue)

        self._poll_queue()

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self._queue.get_nowait()
                self._handle_queue_item(item)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _handle_queue_item(self, item: tuple) -> None:
        kind = item[0]
        if kind.startswith("bulk_"):
            self.bulk_tab.handle_queue(kind, item[1])
        elif kind == "xfer_confirm":
            _, message, event, state = item
            ok = messagebox.askokcancel("Confirm Transfer", message)
            state["ok"] = ok
            event.set()
        elif kind.startswith("xfer_"):
            self.xfer_tab.handle_queue(kind, item[1])


def main() -> None:
    from ocrolus_automations.config import get_settings

    settings = get_settings()
    setup_logging(level=settings.log_level, log_file=settings.log_file or None)
    root = tk.Tk()
    OcrolusApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
