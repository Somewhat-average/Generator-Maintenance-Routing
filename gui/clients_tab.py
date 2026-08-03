import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import manage_clients
import get_matrix
from gui.threading_utils import run_in_background
from gui.client_dialog import ClientDialog


class ClientsTab(ttk.Frame):
    def __init__(self, parent, on_clients_changed):
        super().__init__(parent, padding=10)
        self.on_clients_changed = on_clients_changed
        self.fieldnames = []
        self.rows = []

        self._build_widgets()
        self._load()

    def _build_widgets(self):
        self.status_label = ttk.Label(self, text="", foreground="#555")
        self.status_label.pack(fill="x", pady=(0, 4))

        columns = ("Name", "Plan", "Address", "Phone")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=col)
        self.tree.column("Name", width=160)
        self.tree.column("Plan", width=80)
        self.tree.column("Address", width=280)
        self.tree.column("Phone", width=120)
        self.tree.pack(fill="both", expand=True)

        button_row = ttk.Frame(self)
        button_row.pack(fill="x", pady=(8, 0))
        ttk.Button(button_row, text="Add", command=self._on_add).pack(side="left")
        ttk.Button(button_row, text="Edit", command=self._on_edit).pack(side="left", padx=4)
        ttk.Button(button_row, text="Remove", command=self._on_remove).pack(side="left")
        ttk.Button(button_row, text="Refresh", command=self._load).pack(side="right")

    def _load(self):
        try:
            self.fieldnames, self.rows = manage_clients.load_clients()
            self.status_label.configure(text="")
        except FileNotFoundError:
            self.fieldnames = ["Name"] + manage_clients.EDITABLE_FIELDS + ["Latitude", "Longitude"]
            self.rows = []
            self.status_label.configure(
                text="No generator_clients.csv found - add a client below to create one.")
        self._refresh_tree()

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(self.rows):
            self.tree.insert("", "end", iid=str(i), values=(
                row.get('Name', ''), row.get('Plan', ''), row.get('Address', ''), row.get('Phone', '')))

    def _selected_row(self):
        selection = self.tree.selection()
        if not selection:
            return None
        return self.rows[int(selection[0])]

    def _on_add(self):
        if not self.fieldnames:
            messagebox.showerror("No client file",
                                  "Add a client isn't available until generator_clients.csv exists "
                                  "with a header row.", parent=self)
            return
        new_row = {field: "" for field in self.fieldnames}
        ClientDialog(self, self.fieldnames, new_row, is_new=True,
                     all_rows=self.rows, on_save=self._on_client_saved)

    def _on_edit(self):
        row = self._selected_row()
        if row is None:
            messagebox.showinfo("No selection", "Select a client to edit first.", parent=self)
            return
        ClientDialog(self, self.fieldnames, row, is_new=False,
                     all_rows=self.rows, on_save=self._on_client_saved)

    def _on_remove(self):
        row = self._selected_row()
        if row is None:
            messagebox.showinfo("No selection", "Select a client to remove first.", parent=self)
            return

        name = row.get('Name', '')
        if name in manage_clients.PROTECTED_NAMES:
            typed = simpledialog.askstring(
                "Confirm removal",
                f"'{name}' is used as a route start/end point elsewhere in the app. "
                f"Removing it will break routing. Type the name again to confirm removal:",
                parent=self)
            if typed != name:
                return
        else:
            if not messagebox.askyesno("Remove client",
                                        f"Remove {name} ({row.get('Address', '')})?", parent=self):
                return

        self.rows.remove(row)
        self._save_and_refresh()

    def _on_client_saved(self, row, is_new):
        if is_new:
            self.rows.append(row)
        self._save_and_refresh()

    def _save_and_refresh(self):
        manage_clients.save_clients(self.fieldnames, self.rows)
        self._refresh_tree()
        self.status_label.configure(text="Updating distance/duration matrices...")
        # Call build_matrices directly rather than manage_clients.update_matrices(), which
        # swallows exceptions and only print()s them - invisible in the GUI, and the reason
        # a stale/incomplete matrix could silently break route generation later.
        run_in_background(self, get_matrix.build_matrices, self._on_matrices_updated,
                           manage_clients.CLIENTS_FILE)

    def _on_matrices_updated(self, status, payload):
        if status == "error":
            message = (f"Could not update the distance/duration matrices automatically "
                       f"({payload}). Route generation may fail until this succeeds - "
                       f"click Refresh once you're back online, or run get_matrix.py manually.")
            self.status_label.configure(text=message)
            messagebox.showwarning("Matrix update failed", message, parent=self)
        else:
            self.status_label.configure(text="")
        if self.on_clients_changed:
            self.on_clients_changed()
