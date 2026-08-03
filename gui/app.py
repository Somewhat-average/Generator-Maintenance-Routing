import tkinter as tk
from tkinter import ttk

from gui.clients_tab import ClientsTab
from gui.route_tab import RouteTab


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Generator Maintenance Routing")
        self.geometry("720x640")

        notebook = ttk.Notebook(self)
        self.clients_tab = ClientsTab(notebook, on_clients_changed=self._on_clients_changed)
        self.route_tab = RouteTab(notebook)
        notebook.add(self.clients_tab, text="Manage Clients")
        notebook.add(self.route_tab, text="Generate Route")
        notebook.pack(fill="both", expand=True)

    def _on_clients_changed(self):
        self.route_tab.reload_clients()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
