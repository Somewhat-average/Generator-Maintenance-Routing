import tkinter as tk
from tkinter import ttk, messagebox

import get_matrix
import manage_clients
from gui.threading_utils import run_in_background


class ClientDialog(tk.Toplevel):
    """Modal add/edit form for a single client row.

    `row` is the dict to mutate (a fresh {field: ""} dict for a new client,
    or the actual row object from ClientsTab.rows for an edit - editing
    mutates it in place, matching manage_clients.edit_client's approach).
    on_save(row, is_new) is called once the row has been fully validated,
    geocoded (if needed), and is ready to be persisted by the caller.
    """

    def __init__(self, parent, fieldnames, row, is_new, all_rows, on_save):
        super().__init__(parent)
        self.fieldnames = fieldnames
        self.row = row
        self.is_new = is_new
        self.all_rows = all_rows
        self.on_save = on_save
        self._last_geocoded_address = None if is_new else row.get('Address', '')

        self.title("Add Client" if is_new else f"Edit {row.get('Name', '')}")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self.entries = {}
        self._build_form()

        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_form(self):
        form = ttk.Frame(self, padding=10)
        form.grid(row=0, column=0, sticky="nsew")

        r = 0
        ttk.Label(form, text="Name:").grid(row=r, column=0, sticky="w", pady=2)
        name_entry = ttk.Entry(form, width=32)
        name_entry.insert(0, self.row.get('Name', ''))
        if not self.is_new and self.row.get('Name') in manage_clients.PROTECTED_NAMES:
            name_entry.configure(state="readonly")
        name_entry.grid(row=r, column=1, sticky="ew", pady=2)
        self.entries['Name'] = name_entry
        r += 1

        for field in manage_clients.EDITABLE_FIELDS:
            ttk.Label(form, text=f"{field}:").grid(row=r, column=0, sticky="w", pady=2)
            if field == "Plan":
                combo = ttk.Combobox(form, values=manage_clients.VALID_PLANS,
                                      state="readonly", width=29)
                current = self.row.get('Plan', '')
                combo.set(current if current in manage_clients.VALID_PLANS else manage_clients.VALID_PLANS[-1])
                combo.grid(row=r, column=1, sticky="ew", pady=2)
                self.entries[field] = combo
            else:
                entry = ttk.Entry(form, width=32)
                entry.insert(0, self.row.get(field, ''))
                entry.grid(row=r, column=1, sticky="ew", pady=2)
                self.entries[field] = entry
            r += 1

        ttk.Label(form, text="Latitude:").grid(row=r, column=0, sticky="w", pady=2)
        lat_entry = ttk.Entry(form, width=32)
        lat_entry.insert(0, self.row.get('Latitude', ''))
        lat_entry.grid(row=r, column=1, sticky="ew", pady=2)
        self.entries['Latitude'] = lat_entry
        r += 1

        ttk.Label(form, text="Longitude:").grid(row=r, column=0, sticky="w", pady=2)
        lon_entry = ttk.Entry(form, width=32)
        lon_entry.insert(0, self.row.get('Longitude', ''))
        lon_entry.grid(row=r, column=1, sticky="ew", pady=2)
        self.entries['Longitude'] = lon_entry
        r += 1

        self.status_label = ttk.Label(form, text="", foreground="#555")
        self.status_label.grid(row=r, column=0, columnspan=2, sticky="w", pady=(4, 2))
        r += 1

        button_row = ttk.Frame(form)
        button_row.grid(row=r, column=0, columnspan=2, sticky="e", pady=(8, 0))
        self.cancel_button = ttk.Button(button_row, text="Cancel", command=self.destroy)
        self.cancel_button.pack(side="right", padx=(4, 0))
        self.save_button = ttk.Button(button_row, text="Save", command=self._on_save_clicked)
        self.save_button.pack(side="right")

    def _set_busy(self, busy, status_text=""):
        self.save_button.configure(state="disabled" if busy else "normal")
        self.status_label.configure(text=status_text)

    def _on_save_clicked(self):
        values = {field: self.entries[field].get().strip()
                  for field in ["Name"] + manage_clients.EDITABLE_FIELDS}

        if not values['Name']:
            messagebox.showerror("Missing name", "Name is required.", parent=self)
            return

        old_name = None if self.is_new else self.row.get('Name', '')
        other_rows = [r for r in self.all_rows if r is not self.row]
        if values['Name'] != old_name and manage_clients.find_by_name(other_rows, values['Name']):
            messagebox.showerror("Duplicate name",
                                  f"A client named '{values['Name']}' already exists.", parent=self)
            return

        if old_name and old_name in manage_clients.PROTECTED_NAMES and values['Name'] != old_name:
            confirm = messagebox.askyesno(
                "Rename protected client",
                f"'{old_name}' is used as a route start/end point elsewhere in the app. "
                f"Renaming it will break routing unless main.py is updated too. Continue?",
                parent=self)
            if not confirm:
                return

        normalized_plan = manage_clients.normalize_plan(values['Plan'])
        if normalized_plan is None:
            messagebox.showerror("Invalid plan",
                                  f"Plan must be one of: {', '.join(manage_clients.VALID_PLANS)}",
                                  parent=self)
            return
        values['Plan'] = normalized_plan

        address = values['Address']
        if address and address != self._last_geocoded_address:
            self._set_busy(True, "Looking up coordinates...")
            self._pending_values = values
            run_in_background(self, get_matrix.geocode_address, self._on_geocoded, address)
            return

        self._finalize_save(values)

    def _on_geocoded(self, status, payload):
        values = self._pending_values
        self._last_geocoded_address = values['Address']

        if status == "ok" and payload:
            lat, lon = payload
            self.entries['Latitude'].delete(0, tk.END)
            self.entries['Latitude'].insert(0, str(lat))
            self.entries['Longitude'].delete(0, tk.END)
            self.entries['Longitude'].insert(0, str(lon))
            self._set_busy(False, f"Found: {lat}, {lon}")
            values['Latitude'] = str(lat)
            values['Longitude'] = str(lon)
            self._finalize_save(values)
        else:
            self._set_busy(
                False,
                "Could not find coordinates automatically. Enter Latitude/Longitude "
                "manually (or leave blank), then click Save again.")

    def _finalize_save(self, values):
        self.row.update(values)
        for field in self.fieldnames:
            self.row.setdefault(field, "")
        self.on_save(self.row, self.is_new)
        self.destroy()
