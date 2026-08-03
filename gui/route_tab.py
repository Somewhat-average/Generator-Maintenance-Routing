import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox

import manage_clients
import main
from gui.threading_utils import run_in_background

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class RouteTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.current_route = None
        self.client_vars = []  # list of (client_series, tk.BooleanVar)

        self._build_widgets()
        self.reload_clients()

    def _build_widgets(self):
        top_row = ttk.Frame(self)
        top_row.pack(fill="x")
        ttk.Label(top_row, text="Optimize for:").pack(side="left")
        self.matrix_type_combo = ttk.Combobox(top_row, values=["Distance", "Duration"],
                                               state="readonly", width=12)
        self.matrix_type_combo.set("Distance")
        self.matrix_type_combo.pack(side="left", padx=(4, 0))

        self.status_label = ttk.Label(self, text="", foreground="#555")
        self.status_label.pack(fill="x", pady=(4, 4))

        # Scrollable frame of plan-tier checkboxes, one column per tier
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(canvas_frame, height=220, highlightthickness=0)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        h_scrollbar = ttk.Scrollbar(self, orient="horizontal", command=canvas.xview)
        self.checkbox_frame = ttk.Frame(canvas)
        self.checkbox_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.checkbox_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(fill="x")

        self.generate_button = ttk.Button(self, text="Generate Route", command=self._on_generate)
        self.generate_button.pack(pady=(8, 0))

        results = ttk.Labelframe(self, text="Route", padding=8)
        results.pack(fill="both", expand=True, pady=(8, 0))

        self.eta_label = ttk.Label(results, text="")
        self.eta_label.pack(anchor="w")

        self.summary_text = tk.Text(results, height=8, wrap="word", state="disabled")
        self.summary_text.pack(fill="both", expand=True, pady=(4, 4))

        self.maps_button = ttk.Button(results, text="Open in Google Maps",
                                       command=self._on_open_maps, state="disabled")
        self.maps_button.pack(anchor="w")

        calendar_row = ttk.Frame(results)
        calendar_row.pack(fill="x", pady=(8, 0))
        ttk.Label(calendar_row, text="Day:").pack(side="left")
        self.weekday_combo = ttk.Combobox(calendar_row, values=WEEKDAYS, state="readonly", width=12)
        self.weekday_combo.set(WEEKDAYS[0])
        self.weekday_combo.pack(side="left", padx=(4, 8))
        self.calendar_button = ttk.Button(calendar_row, text="Add to Calendar",
                                           command=self._on_add_to_calendar, state="disabled")
        self.calendar_button.pack(side="left")

    def reload_clients(self):
        for widget in self.checkbox_frame.winfo_children():
            widget.destroy()
        self.client_vars = []

        try:
            clients = main.load_clients()
        except FileNotFoundError:
            ttk.Label(self.checkbox_frame, text="No clients found.").pack(anchor="w")
            return

        grouped = main.group_clients_by_plan(clients)
        for plan in manage_clients.VALID_PLANS:
            tier_clients = grouped.get(plan)
            if not tier_clients:
                continue
            tier_frame = ttk.Labelframe(self.checkbox_frame, text=f"{plan} plan", padding=4)
            tier_frame.pack(side="left", fill="y", padx=4, anchor="n")
            for client in tier_clients:
                var = tk.BooleanVar(value=(plan == "Platinum"))
                ttk.Checkbutton(tier_frame, text=client['Name'], variable=var).pack(anchor="w")
                self.client_vars.append((client, var))

    def _selected_clients(self):
        return [client for client, var in self.client_vars if var.get()]

    def _on_generate(self):
        selected = self._selected_clients()
        if not selected:
            messagebox.showinfo("No clients selected", "Select at least one client first.", parent=self)
            return

        matrix_type = self.matrix_type_combo.get().lower()
        self.generate_button.configure(state="disabled")
        self.status_label.configure(text="Solving route...")
        run_in_background(self, self._build_route_worker, self._on_route_built,
                           matrix_type, selected)

    def _build_route_worker(self, matrix_type, selected):
        clients = main.load_clients()
        matrix = main.load_matrix(matrix_type)
        return main.build_route(clients, matrix, selected, matrix_type=matrix_type)

    def _on_route_built(self, status, payload):
        self.generate_button.configure(state="normal")

        if status == "error":
            self.status_label.configure(text="")
            messagebox.showerror("Could not generate route", str(payload), parent=self)
            return

        self.current_route = payload
        self.status_label.configure(text="")

        if payload["eta_lower"] is not None:
            self.eta_label.configure(
                text=f"Estimated drive time per stop: {payload['eta_lower']:.0f}-{payload['eta_upper']:.0f} minutes")
        else:
            self.eta_label.configure(text="")

        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert("1.0", payload["summary_text"])
        self.summary_text.configure(state="disabled")

        self.maps_button.configure(state="normal")
        self.calendar_button.configure(state="normal")

    def _on_open_maps(self):
        if self.current_route:
            webbrowser.open(self.current_route["google_maps_url"])

    def _on_add_to_calendar(self):
        if not self.current_route:
            return
        day_index = WEEKDAYS.index(self.weekday_combo.get()) + 1
        self.calendar_button.configure(state="disabled")
        self.status_label.configure(text="Adding events to Google Calendar (check your browser for sign-in)...")
        run_in_background(self, self._add_to_calendar_worker, self._on_calendar_done, day_index)

    def _add_to_calendar_worker(self, day_index):
        route = self.current_route
        main.create_calendar_events(route["ordered_clients"], route["google_maps_short_link"],
                                     main.resolve_weekday(day_index), main.get_calendar_id())

    def _on_calendar_done(self, status, payload):
        self.calendar_button.configure(state="normal")
        self.status_label.configure(text="")
        if status == "error":
            messagebox.showerror("Could not add to calendar", str(payload), parent=self)
        else:
            messagebox.showinfo("Calendar updated", "Events added to Google Calendar.", parent=self)
